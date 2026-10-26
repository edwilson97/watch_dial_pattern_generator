"""Real VTK rendering and camera-interaction regressions; requires a display."""
import tempfile
import subprocess
import sys
import textwrap
import time
import unittest
from concurrent.futures import Future
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
from PIL import Image

from dial_patterns import render, save_map
from inspection import ReliefViewer, relief_mesh, open_inspection, write_snapshot, SnapshotReader, InspectionUpdates


def camera_values(plotter):
    return np.array([plotter.camera.position, plotter.camera.focal_point,
                     plotter.camera.up])


class UpdateTests(unittest.TestCase):
    def test_live_timer_has_initialized_native_window(self):
        # Model Win32: a timer permanently captures the window at creation.
        interactor = Mock(initialized=False)
        def initialize():
            interactor.initialized = True
        def create_timer(duration):
            self.assertTrue(interactor.initialized,
                            'Timer created before the native window exists')
        interactor.initialize.side_effect = initialize
        interactor.create_timer.side_effect = create_timer
        viewer = ReliefViewer.__new__(ReliefViewer)
        viewer.plotter = Mock(iren=interactor)
        reader = Mock()
        ReliefViewer.watch_source(viewer, reader)
        interactor.create_timer.assert_called_once_with(150)
        # An already initialized window should not be initialized again.
        ReliefViewer.watch_source(viewer, reader)
        interactor.initialize.assert_called_once_with()

    def test_rapid_edits_coalesce_and_stale_renders_are_discarded(self):
        class Parent:
            def __init__(self):
                self.timers = {}
                self.next_id = 0
            def bind(self, *args, **kwargs):
                pass
            def after(self, delay, callback):
                self.next_id += 1
                self.timers[self.next_id] = (delay, callback)
                return self.next_id
            def after_cancel(self, timer):
                self.timers.pop(timer, None)
            def run(self, delay):
                timer = next(key for key, value in self.timers.items() if value[0] == delay)
                self.timers.pop(timer)[1]()

        parent, session = Parent(), Mock()
        params = {'pitch_mm': 1}
        first, last = Future(), Future()
        with patch('inspection.ThreadPoolExecutor') as executor:
            executor.return_value.submit.side_effect = [first, last]
            updates = InspectionUpdates(parent, lambda: dict(params), Mock(), Mock())
            updates.sessions.append(session)
            updates.schedule()
            updates.schedule()
            self.assertEqual(len(parent.timers), 1)
            parent.run(350)
            params['pitch_mm'] = 2
            updates.schedule()
            parent.run(350)
            self.assertEqual(executor.return_value.submit.call_count, 1)
            first.set_result((np.zeros((2,2)), {'pattern_name': 'old'}))
            parent.run(50)
            session.update.assert_not_called()
            self.assertEqual(executor.return_value.submit.call_args.kwargs, {'pitch_mm': 2})
            last.set_result((np.ones((2,2)), {'pattern_name': 'new'}))
            parent.run(50)
            session.update.assert_called_once()
            np.testing.assert_array_equal(session.update.call_args.args[0], np.ones((2,2)))
            updates.close()
            self.assertFalse(parent.timers)


class MeshTests(unittest.TestCase):
    def test_native_viewer_signals_ready_while_still_open(self):
        parent, on_ready = Mock(), Mock()
        array, meta = render(pattern='brick', pixels=128)
        session = open_inspection(parent, array, meta, on_ready=on_ready)
        try:
            deadline = time.monotonic() + 15
            while not on_ready.called and time.monotonic() < deadline:
                parent.after.call_args.args[1]()
                time.sleep(.05)
            on_ready.assert_called_once_with()
            self.assertTrue(session.alive())
        finally:
            if session.alive():
                session.process.terminate()
                session.process.wait(timeout=5)
            with patch('tkinter.messagebox.showerror'):
                parent.after.call_args.args[1]()

    def test_native_viewer_polls_changes_after_startup(self):
        script = textwrap.dedent('''
            import sys, time
            from pathlib import Path
            from dial_patterns import render
            from inspection import ReliefViewer, SnapshotReader, write_snapshot
            source = Path(sys.argv[1])
            a, m = render(pattern='brick', pixels=128)
            write_snapshot(source, a, m)
            reader = SnapshotReader(source)
            viewer = ReliefViewer(*reader.read())
            viewer.watch_source(reader)
            viewer.plotter.show(interactive_update=True, auto_close=False)
            a, m = render(pattern='wave', pixels=256)
            write_snapshot(source, a, m)
            deadline = time.monotonic() + 5
            while viewer.meta['pattern'] != 'wave' and time.monotonic() < deadline:
                viewer.plotter.update()
                time.sleep(.01)
            assert viewer.meta['pattern'] == 'wave', 'Native update timer did not fire'
            viewer.plotter.close()
        ''')
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-c', script, str(Path(directory)/'source.npz')],
                                    cwd=Path(__file__).resolve().parent.parent, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_mesh_keeps_depth_spacing_orientation_and_sampling(self):
        source = np.zeros((7, 7), dtype=np.uint16)
        source[0, 0] = 65535
        source[-1, -1] = 32768
        mesh = relief_mesh(source, 7, .2, max_samples=4)
        self.assertEqual(mesh.n_points, 16)
        # Original pixels have 1 mm spacing, and retained indices are 0,2,4,6.
        np.testing.assert_allclose(mesh.points[0], [-3, 3, 0])
        np.testing.assert_allclose(mesh.points[-1], [3, -3, (32768/65535-1)*.2])
        np.testing.assert_allclose(mesh['Depth (mm)'], -mesh.points[:, 2])

    def test_launcher_transfers_snapshot_and_cleans_up(self):
        class Parent:
            def after(self, delay, callback):
                self.callback = callback
            def bind(self, *args, **kwargs):
                self.destroy_callback = args[1]
                return 'binding'
            def unbind(self, *args):
                pass
        parent = Parent()
        source, meta = render(pattern='brick', pixels=128)
        with patch('inspection.subprocess.Popen') as popen:
            process = popen.return_value
            process.poll.return_value = None
            process.returncode = 0
            on_ready = Mock()
            session = open_inspection(parent, source, meta, on_ready=on_ready)
            self.assertIs(session.process, process)
            path = Path(popen.call_args.args[0][-1])
            parent.callback()
            on_ready.assert_not_called()
            path.with_name('ready').touch()
            parent.callback()
            on_ready.assert_called_once_with()
            parent.callback()
            on_ready.assert_called_once_with()
            with np.load(path, allow_pickle=False) as snapshot:
                np.testing.assert_array_equal(snapshot['array'], source)
            reader = SnapshotReader(path)
            reader.read()
            updated = source.copy()
            updated[0, 0] ^= 65535
            session.update(updated, meta)
            self.assertTrue(reader.changed())
            np.testing.assert_array_equal(reader.read()[0], updated)
            self.assertFalse(reader.changed())
            process.poll.return_value = 0
            parent.callback()
            self.assertFalse(path.parent.exists())

    def test_launcher_restores_cursor_when_process_fails_before_ready(self):
        parent, on_ready = Mock(), Mock()
        source, meta = render(pattern='brick', pixels=128)
        with patch('inspection.subprocess.Popen') as popen, \
             patch('tkinter.messagebox.showerror') as showerror:
            process = popen.return_value
            process.poll.return_value = 1
            process.returncode = 1
            open_inspection(parent, source, meta, on_ready=on_ready)
            path = Path(popen.call_args.args[0][-1])
            path.with_name('error.txt').write_text('Startup failed')
            parent.after.call_args.args[1]()
            on_ready.assert_called_once_with()
            showerror.assert_called_once_with('Inspection failed', 'Startup failed', parent=parent)
            self.assertFalse(path.parent.exists())


class ViewerTests(unittest.TestCase):
    def setUp(self):
        self.array, self.meta = render(pattern='brick', pixels=256, size_mm=4)
        self.original = self.array.copy()
        self.viewer = ReliefViewer(self.array, self.meta, off_screen=True)
        self.viewer.plotter.show(auto_close=False, interactive=False)

    def tearDown(self):
        self.viewer.plotter.close()

    def test_auto_detail_and_source_resolution_guidance(self):
        viewer = self.viewer
        source, meta = render(pattern='isometriccubes', size_mm=4, pixels=1024)
        viewer.replace_source(source, meta)
        self.assertIsNone(viewer.settings['samples'])
        self.assertEqual(viewer.mesh.dimensions[:2], (801, 801))
        status = viewer.plotter.actors['status'].GetText(3)
        self.assertNotIn('few source pixels', status)
        viewer.set_detail('Mesh: Fast (201)')
        self.assertIn('few mesh samples', viewer.plotter.actors['status'].GetText(3))
        viewer.set_detail('Mesh: Auto (groove detail)')
        self.assertEqual(viewer.mesh.dimensions[:2], (801, 801))
        source, meta = render(pattern='isometriccubes', size_mm=4, pixels=128)
        viewer.replace_source(source, meta)
        self.assertIn('few source pixels', viewer.plotter.actors['status'].GetText(3))
        self.assertEqual(viewer.mesh.dimensions[:2], (128, 128))
        np.testing.assert_array_equal(viewer.array, source)

    def test_real_mouse_navigation_and_preserved_camera(self):
        viewer = self.viewer
        plotter = viewer.plotter
        interactor = plotter.iren.interactor
        before = camera_values(plotter)
        interactor.SetEventInformation(640, 450, 0, 0)
        interactor.LeftButtonPressEvent()
        interactor.SetEventInformation(720, 500, 0, 0)
        interactor.MouseMoveEvent()
        interactor.LeftButtonReleaseEvent()
        self.assertFalse(np.allclose(before, camera_values(plotter)))
        before_pan = np.array(plotter.camera.focal_point)
        interactor.SetEventInformation(640, 450, 0, 1)
        interactor.LeftButtonPressEvent()
        interactor.SetEventInformation(690, 450, 0, 1)
        interactor.MouseMoveEvent()
        interactor.LeftButtonReleaseEvent()
        self.assertFalse(np.allclose(before_pan, plotter.camera.focal_point))
        before_zoom = plotter.camera.distance
        interactor.MouseWheelForwardEvent()
        self.assertNotAlmostEqual(before_zoom, plotter.camera.distance)
        camera = camera_values(plotter)
        viewer.change('span', 2.)
        viewer.change('x', 1.)
        viewer.change('exaggeration', 5.)
        viewer.set_detail('Mesh: Fast (201)')
        viewer.toggle_colors()
        np.testing.assert_allclose(camera, camera_values(plotter))
        self.assertEqual(tuple(viewer.actor.GetScale()), (1., 1., 5.))
        np.testing.assert_array_equal(self.array, self.original)

    def test_live_source_timer_preserves_view_and_updates_bounds(self):
        viewer = self.viewer
        viewer.change('exaggeration', 4.)
        viewer.change('x', 1.5)
        viewer.toggle_colors()
        viewer.toggle_projection()
        camera = camera_values(viewer.plotter)
        scale = viewer.plotter.camera.parallel_scale
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'source.npz'
            write_snapshot(path, self.array, self.meta)
            reader = SnapshotReader(path)
            reader.read()
            viewer.watch_source(reader)
            updated, meta = render(pattern='wave', pixels=128, size_mm=2, depth_mm=.3)
            write_snapshot(path, updated, meta)
            # Dispatch the same event as the native repeating timer.
            viewer.plotter.iren.interactor.InvokeEvent('TimerEvent')
            self.assertEqual(viewer.meta['pattern'], 'wave')
            np.testing.assert_array_equal(viewer.array, updated)
            np.testing.assert_allclose(camera, camera_values(viewer.plotter))
            self.assertEqual(viewer.plotter.camera.parallel_scale, scale)
            self.assertEqual(viewer.settings['exaggeration'], 4.)
            self.assertTrue(viewer.height_colors)
            self.assertEqual(viewer.settings['span'], 2.)
            self.assertEqual(viewer.settings['x'], 1.)
            self.assertEqual(viewer.sliders['span'].GetRepresentation().GetMaximumValue(), 2.)
            # Grayscale mode follows subsequent edits without changing its camera.
            viewer.toggle_gray()
            gray_camera = camera_values(viewer.plotter)
            updated, meta = render(pattern='honeycomb', pixels=256, size_mm=6)
            write_snapshot(path, updated, meta)
            viewer.plotter.iren.interactor.InvokeEvent('TimerEvent')
            self.assertTrue(viewer.gray_actor.GetVisibility())
            self.assertFalse(viewer.actor.GetVisibility())
            np.testing.assert_allclose(gray_camera, camera_values(viewer.plotter))

    def test_presets_height_map_and_screenshot_leave_exports_intact(self):
        viewer = self.viewer
        for preset in ('top', 'front', 'iso'):
            viewer.view(preset)
        camera = camera_values(viewer.plotter)
        projection = viewer.plotter.camera.parallel_projection
        viewer.toggle_gray()
        self.assertFalse(viewer.actor.GetVisibility())
        self.assertTrue(viewer.gray_actor.GetVisibility())
        self.assertTrue(viewer.plotter.camera.parallel_projection)
        viewer.toggle_gray()
        np.testing.assert_allclose(camera, camera_values(viewer.plotter))
        self.assertEqual(projection, viewer.plotter.camera.parallel_projection)
        viewer.toggle_projection()
        self.assertNotEqual(projection, viewer.plotter.camera.parallel_projection)
        with tempfile.TemporaryDirectory() as directory:
            screenshot = Path(directory)/'inspection.png'
            with patch('inspection.screenshot_path', return_value=str(screenshot)):
                viewer.save_screenshot()
            with Image.open(screenshot) as image:
                self.assertEqual(image.size, (1280, 900))
            depth = save_map(self.array, self.meta, Path(directory)/'depth.png')
            np.testing.assert_array_equal(np.asarray(Image.open(depth)), self.original)


if __name__ == '__main__':
    unittest.main()
