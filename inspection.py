"""Interactive PyVista relief inspection; never used for engraving export."""
import importlib.util
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np


def write_snapshot(source, array, meta):
    """Publish a complete frame atomically, so readers never see partial data."""
    temporary = source.with_suffix('.next.npz')
    try:
        with temporary.open('wb') as stream:
            np.savez(stream, array=array, meta=json.dumps(meta))
        temporary.replace(source)
    finally:
        temporary.unlink(missing_ok=True)


class SnapshotReader:
    def __init__(self, source):
        self.source = Path(source)
        self.revision = None

    @staticmethod
    def stamp(stat):
        return stat.st_ino, stat.st_mtime_ns, stat.st_size

    def read(self):
        with self.source.open('rb') as stream:
            revision = self.stamp(os.fstat(stream.fileno()))
            with np.load(stream, allow_pickle=False) as data:
                array, meta = data['array'], json.loads(str(data['meta']))
        self.revision = revision
        return array, meta

    def changed(self):
        return self.stamp(self.source.stat()) != self.revision


class InspectionSession:
    def __init__(self, process, source):
        self.process, self.source = process, source

    def alive(self):
        return self.process.poll() is None

    def update(self, array, meta):
        if self.alive():
            write_snapshot(self.source, array, meta)


class InspectionUpdates:
    """Debounce edits and render off the Tk thread; keep only the newest result."""
    def __init__(self, parent, params, render, status):
        self.parent, self.params, self.render, self.status = parent, params, render, status
        self.sessions = []
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='dial-inspection')
        self.revision = 0
        self.debounce = self.poll_timer = self.future = self.pending = None
        self.closed = False
        parent.bind('<Destroy>', lambda event: self.close() if event.widget is parent else None, add='+')

    def schedule(self, *_):
        self.revision += 1
        if self.debounce is not None:
            self.parent.after_cancel(self.debounce)
            self.debounce = None
        self.sessions = [session for session in self.sessions if session.alive()]
        if self.sessions and not self.closed:
            self.debounce = self.parent.after(350, self.start)

    def start(self):
        self.debounce = None
        try:
            params = self.params()
        except (ValueError, TypeError) as exc:
            self.status('3D update paused: ' + str(exc))
            return
        if self.future is not None:
            self.pending = self.revision, params
        else:
            self.submit(self.revision, params)

    def submit(self, revision, params):
        self.render_revision = revision
        self.future = self.executor.submit(self.render, **params)
        self.poll_timer = self.parent.after(50, self.poll)

    def poll(self):
        self.poll_timer = None
        if self.closed:
            return
        if not self.future.done():
            self.poll_timer = self.parent.after(50, self.poll)
            return
        try:
            array, meta = self.future.result()
            if self.render_revision == self.revision:
                self.sessions = [session for session in self.sessions if session.alive()]
                for session in self.sessions:
                    session.update(array, meta)
                if self.sessions:
                    self.status(f'{meta["pattern_name"]} | 3D viewers updated | white = high')
        except Exception as exc:
            if self.render_revision == self.revision:
                self.status('3D update paused: ' + str(exc))
        self.future = None
        pending, self.pending = self.pending, None
        if pending is not None and pending[0] == self.revision and self.sessions:
            self.submit(*pending)

    def close(self):
        self.closed = True
        for timer in (self.debounce, self.poll_timer):
            if timer is not None:
                self.parent.after_cancel(timer)
        self.executor.shutdown(wait=False, cancel_futures=True)


def helper_command(*args):
    """Re-enter the bundled app, or run this module with the source interpreter."""
    if getattr(sys, 'frozen', False):
        return [sys.executable, '--inspection-helper', *map(str, args)]
    return [sys.executable, str(Path(__file__).resolve()), *map(str, args)]


def screenshot_path(initial_name):
    """Run Tk's native save dialog outside VTK's Cocoa application on macOS."""
    # A file also works in windowed bundles, where stdout is unavailable.
    with tempfile.TemporaryDirectory(prefix='dial-screenshot-') as directory:
        result = Path(directory)/'selection.txt'
        subprocess.run(helper_command('--screenshot-dialog', initial_name, result), check=True)
        return result.read_text(encoding='utf-8')


def screenshot_dialog(initial_name, result):
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    try:
        name = filedialog.asksaveasfilename(
            parent=root, title='Save inspection screenshot', defaultextension='.png',
            initialfile=initial_name, filetypes=[('PNG image', '*.png')])
        Path(result).write_text(name, encoding='utf-8')
    finally:
        root.destroy()


def crop_map(array, meta, span_mm, center_x=0., center_y=0.):
    """Crop full-resolution samples; center is in mm relative to dial center."""
    n = array.shape[0]
    span_mm = min(meta['size_mm'], max(meta['size_mm']/n*2, span_mm))
    count = min(n, max(2, round(span_mm/meta['size_mm']*n)))
    cx = round((center_x/meta['size_mm']+.5)*n)
    cy = round((center_y/meta['size_mm']+.5)*n)
    x0 = min(n-count, max(0, cx-count//2))
    y0 = min(n-count, max(0, cy-count//2))
    return array[y0:y0+count, x0:x0+count], count*meta['size_mm']/n


def relief_mesh(array, span_mm, depth_mm, max_samples=401):
    """Sample source pixel centers, preserving physical spacing and depth values."""
    import pyvista as pv
    n = array.shape[0]
    indices = np.unique(np.linspace(0, n-1, min(n, max_samples), dtype=int))
    xy = (indices-(n-1)/2)*span_mm/n
    x, y = np.meshgrid(xy, -xy)  # Image row zero is at the top (+Y).
    z = (array[np.ix_(indices, indices)].astype(float)/65535-1)*depth_mm
    mesh = pv.StructuredGrid(x, y, z)
    mesh['Depth (mm)'] = (-z).ravel(order='F')
    return mesh


class ReliefViewer:
    """A native VTK window with continuous mouse navigation and live controls."""
    def __init__(self, array, meta, *, off_screen=False):
        import pyvista as pv
        self.pv = pv
        self.array = array
        self.meta = meta
        self.settings = dict(span=min(4., meta['size_mm']), x=0., y=0.,
                             exaggeration=1., samples=401)
        self.height_colors = False
        self.gray = False
        self.mesh = None
        self.actor = None
        self.gray_actor = None
        self.surface_camera = None
        self.sliders = {}
        self.plotter = pv.Plotter(title='Relief inspection — '+meta['pattern_name'],
                                 window_size=(1280, 900), off_screen=off_screen)
        self.plotter.set_background('#1b1e23')
        self.plotter.enable_terrain_style(mouse_wheel_zooms=True, shift_pans=True)
        self.plotter.enable_anti_aliasing('fxaa')
        self.plotter.add_axes(viewport=(0, .25, .13, .40))
        self.plotter.add_text(
            'Drag: orbit / tilt    Shift + drag: pan    Wheel: zoom\n'
            'T: top    F: front    I: isometric    R: fit    P: projection\n'
            'G: height map / 3D    C: height colors    S: save screenshot',
            position='upper_left', font_size=11, color='#d5dce5', name='help')
        self.update_surface(fit=True)
        # VTK widgets stay live; no Refresh button or image re-rendering loop.
        for key, title, limits, a, b in (
            ('span', 'Crop width (mm)', (min(.25, meta['size_mm']), meta['size_mm']), (.04,.16), (.31,.16)),
            ('x', 'Crop center X (mm)', (-meta['size_mm']/2, meta['size_mm']/2), (.365,.16), (.635,.16)),
            ('y', 'Crop center Y (mm)', (-meta['size_mm']/2, meta['size_mm']/2), (.69,.16), (.96,.16)),
            ('exaggeration', 'Depth exaggeration', (1,10), (.04,.06), (.44,.06)),
        ):
            widget = self.plotter.add_slider_widget(
                lambda value, key=key: self.change(key, value), limits,
                value=self.settings[key], title=title, pointa=a, pointb=b,
                style='modern', color='#cad5e3', title_height=.018,
                interaction_event='always' if key=='exaggeration' else 'end', fmt='%.2f')
            self.compact_slider(widget)
            self.sliders[key] = widget
        detail_widget = self.plotter.add_text_slider_widget(
            self.set_detail, ['Mesh: Fast (201)', 'Mesh: Balanced (401)', 'Mesh: Fine (801)'], value=1,
            pointa=(.58,.06), pointb=(.96,.06),
            style='modern', color='#cad5e3', interaction_event='end')
        self.compact_slider(detail_widget)
        for key, callback in {
            't': lambda: self.view('top'), 'f': lambda: self.view('front'),
            'i': lambda: self.view('iso'), 'r': self.fit,
            'p': self.toggle_projection, 'g': self.toggle_gray,
            'c': self.toggle_colors, 's': self.save_screenshot,
        }.items():
            self.plotter.clear_events_for_key(key)
            self.plotter.add_key_event(key, callback)

    def replace_source(self, array, meta):
        """Refresh source geometry without resetting the user's camera or modes."""
        self.array, self.meta = array, meta
        size = meta['size_mm']
        limits = dict(span=(min(.25, size), size), x=(-size/2, size/2), y=(-size/2, size/2))
        for key, (low, high) in limits.items():
            self.settings[key] = min(high, max(low, self.settings[key]))
            representation = self.sliders[key].GetRepresentation()
            representation.SetMinimumValue(low)
            representation.SetMaximumValue(high)
            representation.SetValue(self.settings[key])
        self.plotter.render_window.SetWindowName('Relief inspection — '+meta['pattern_name'])
        self.update_surface()

    def watch_source(self, reader):
        def refresh(_interactor, _event):
            try:
                if reader.changed():
                    self.replace_source(*reader.read())
                    self.plotter.remove_actor('update-error', render=False)
            except (OSError, ValueError) as exc:
                self.plotter.add_text('Live update paused: '+str(exc), position='lower_left',
                                      font_size=10, name='update-error')
        self.plotter.iren.add_observer('TimerEvent', refresh)
        self.plotter.iren.create_timer(150)

    @staticmethod
    def compact_slider(widget):
        representation = widget.GetRepresentation()
        representation.SetTitleHeight(.018)
        representation.SetLabelHeight(.018)
        representation.SetTubeWidth(.006)
        representation.SetSliderWidth(.018)
        representation.SetSliderLength(.025)

    def change(self, key, value):
        if self.settings[key] == value:
            return
        self.settings[key] = value
        if key == 'exaggeration':
            self.actor.SetScale(1, 1, value)
            self.plotter.reset_camera_clipping_range()
            self.update_status()
            self.plotter.render()
        else:
            self.update_surface()

    def set_detail(self, value):
        samples = {'Mesh: Fast (201)': 201, 'Mesh: Balanced (401)': 401,
                   'Mesh: Fine (801)': 801}[value]
        if samples != self.settings['samples']:
            self.settings['samples'] = samples
            self.update_surface()

    def update_surface(self, fit=False):
        crop, span = crop_map(self.array, self.meta, self.settings['span'],
                              self.settings['x'], self.settings['y'])
        self.crop, self.span = crop, span
        self.mesh = relief_mesh(crop, span, self.meta['depth_mm'], self.settings['samples'])
        camera = self.plotter.camera_position if self.actor is not None else None
        self.actor = self.plotter.add_mesh(
            self.mesh, name='relief', color='#bcc8d7', smooth_shading=False,
            scalars='Depth (mm)' if self.height_colors else None,
            cmap='viridis_r', clim=(0, max(self.meta['depth_mm'], 1e-9)),
            show_scalar_bar=False, ambient=.25, diffuse=.7, specular=.25,
            specular_power=35, reset_camera=False)
        self.actor.SetScale(1, 1, self.settings['exaggeration'])
        self.actor.SetVisibility(not self.gray)
        # Full-resolution nearest-neighbor texture retains narrow grooves when
        # the navigation mesh has fewer samples than the source height map.
        edge = (crop.shape[0]-1)*span/crop.shape[0]/2
        plane = self.pv.Plane(center=(0,0,0), direction=(0,0,1),
                              i_size=2*edge, j_size=2*edge)
        image = np.repeat((crop/257).astype(np.uint8)[...,None], 3, axis=2)
        texture = self.pv.numpy_to_texture(image)
        texture.interpolate = False
        self.gray_actor = self.plotter.add_mesh(plane, texture=texture, lighting=False,
                                                name='height-map', reset_camera=False)
        self.gray_actor.SetVisibility(self.gray)
        if camera is not None:
            self.plotter.camera_position = camera
        if fit:
            self.plotter.view_isometric()
            self.fit()
        self.plotter.reset_camera_clipping_range()
        self.update_status()
        self.plotter.render()

    def update_status(self):
        mode = 'HEIGHT MAP (source pixels)' if self.gray else '3D SURFACE'
        self.plotter.add_text(
            f'{self.meta["pattern_name"]} | {mode}\n'
            f'INSPECTION ONLY | {self.span:.3f} mm crop | Z x{self.settings["exaggeration"]:g}\n'
            f'{self.crop.shape[0]} source pixels | {self.mesh.dimensions[0]} mesh samples / side\n'
            f'Design depth: {self.meta["depth_mm"]:.3f} mm | depth is not laser calibration',
            position='upper_right', font_size=10, color='#d5dce5', name='status')

    def fit(self):
        self.plotter.reset_camera()
        # Leave room for the controls at the bottom of the viewport.
        self.plotter.camera.zoom(.75)
        self.plotter.render()

    def view(self, preset):
        if self.gray and preset != 'top':
            self.toggle_gray()
        if preset == 'top':
            self.plotter.view_xy()
        elif preset == 'front':
            self.plotter.view_xz()
        else:
            self.plotter.view_isometric()
        self.fit()

    def toggle_projection(self):
        self.plotter.camera.parallel_projection = not self.plotter.camera.parallel_projection
        self.plotter.reset_camera_clipping_range()
        self.plotter.render()

    def toggle_gray(self):
        self.gray = not self.gray
        self.actor.SetVisibility(not self.gray)
        self.gray_actor.SetVisibility(self.gray)
        if self.gray:
            self.surface_camera = (self.plotter.camera_position, self.plotter.camera.parallel_projection)
            self.plotter.view_xy()
            self.plotter.enable_parallel_projection()
            self.fit()
        elif self.surface_camera:
            position, parallel = self.surface_camera
            self.plotter.camera_position = position
            self.plotter.camera.parallel_projection = parallel
        self.plotter.reset_camera_clipping_range()
        self.update_status()
        self.plotter.render()

    def toggle_colors(self):
        self.height_colors = not self.height_colors
        self.update_surface()

    def save_screenshot(self):
        filename = screenshot_path(self.meta['pattern']+'_inspection_only.png')
        if filename:
            self.plotter.screenshot(filename)

    def show(self):
        self.plotter.show()


def open_inspection(parent, array, meta, on_ready=None):
    """Launch an isolated native viewer without blocking Tk's event loop."""
    if importlib.util.find_spec('pyvista') is None:
        raise RuntimeError('PyVista is required for 3D inspection. Install requirements.txt '
                           'using Python 3.12 or 3.13, then launch the app with that Python.')
    directory = tempfile.TemporaryDirectory(prefix='dial-inspection-')
    source = Path(directory.name)/'source.npz'
    errors = Path(directory.name)/'error.txt'
    ready = Path(directory.name)/'ready'
    write_snapshot(source, array, meta)
    try:
        process = subprocess.Popen(helper_command(source))
    except Exception:
        directory.cleanup()
        raise

    def poll():
        nonlocal on_ready
        running = process.poll() is None
        if on_ready is not None and (ready.exists() or not running):
            callback, on_ready = on_ready, None
            callback()
        if running:
            parent.after(250, poll)
            return
        try:
            if process.returncode:
                from tkinter import messagebox
                detail = errors.read_text() if errors.exists() else f'Viewer exited with code {process.returncode}.'
                messagebox.showerror('Inspection failed', detail, parent=parent)
        finally:
            directory.cleanup()
            parent.unbind('<Destroy>', binding)

    def close(event):
        if event.widget is parent:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            directory.cleanup()

    binding = parent.bind('<Destroy>', close, add='+')
    parent.after(250, poll)
    return InspectionSession(process, source)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[0] == '--screenshot-dialog':
        screenshot_dialog(argv[1], argv[2])
        return
    source = Path(argv[0])
    try:
        reader = SnapshotReader(source)
        viewer = ReliefViewer(*reader.read())
        viewer.watch_source(reader)
        def signal_ready(plotter):
            ready = source.with_name('ready')
            if not ready.exists():
                ready.touch()
        viewer.plotter.add_on_render_callback(signal_ready)
        viewer.show()
    except Exception as exc:
        source.with_name('error.txt').write_text(str(exc))
        raise


if __name__ == '__main__':
    main()
