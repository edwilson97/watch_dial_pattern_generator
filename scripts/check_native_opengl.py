"""Check native OpenGL before running interactive viewer tests.

Windows CI must use Mesa's llvmpipe through Win32, preserving native timers.
Run this with the isolated test Python that has Mesa beside its executable.
"""
import sys

import vtkmodules.vtkRenderingOpenGL2  # Register OpenGL render-window classes.
from vtkmodules.vtkRenderingCore import vtkRenderWindow, vtkRenderer


def main():
    window = vtkRenderWindow()
    try:
        backend = window.GetClassName()
        print('Native rendering backend:', backend, flush=True)
        if sys.platform == 'win32' and backend != 'vtkWin32OpenGLRenderWindow':
            raise RuntimeError('Windows viewer tests require a native Win32 window.')
        window.SetSize(64, 64)
        window.AddRenderer(vtkRenderer())
        window.Render()
        if not window.SupportsOpenGL():
            raise RuntimeError('The native render window does not support OpenGL.')
        capabilities = window.ReportCapabilities()
        print(capabilities, flush=True)
        if sys.platform == 'win32' and 'llvmpipe' not in capabilities.lower():
            raise RuntimeError('Windows CI must render with the Mesa llvmpipe driver.')
    finally:
        window.Finalize()


if __name__ == '__main__':
    main()
