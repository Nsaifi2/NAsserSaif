"""Build the offline single-file 3D game; uses only the Python standard library."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
shell=(root/'src3d/shell.html').read_text()
engine=(root/'vendor/three-0.160.1.min.js').read_text()
code=(root/'src3d/game.js').read_text()
assert '</script' not in engine.lower() and '</script' not in code.lower()
(root/'gameplay3d.html').write_text(shell.replace('/* THREE_ENGINE */',engine).replace('/* GAME_CODE */',code))
print('Built gameplay3d.html (offline, Three.js 0.160.1, MIT license in vendor/THREE-LICENSE.txt)')
