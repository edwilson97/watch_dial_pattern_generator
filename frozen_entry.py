"""Entry point for the standalone desktop app and its helper processes."""
import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--inspection-helper':
        from inspection import main as inspection_main
        inspection_main(sys.argv[2:])
    elif len(sys.argv) > 1 and sys.argv[1] == '--bundle-check':
        # Exercise bundled Tk, Pillow, and VTK without requiring a GPU or dialog.
        import tkinter as tk
        from PIL import Image, ImageTk
        from dial_patterns import render
        from inspection import relief_mesh
        root = tk.Tk()
        root.withdraw()
        image = ImageTk.PhotoImage(Image.new('L', (16, 16)), master=root)
        root.update()
        assert image.width() == 16
        root.destroy()
        array, meta = render(pattern='brick', pixels=128)
        mesh = relief_mesh(array, meta['size_mm'], meta['depth_mm'])
        assert mesh.n_points > 0
    else:
        from dial_patterns import main as app_main
        app_main()


if __name__ == '__main__':
    main()
