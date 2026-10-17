# VisionFix — Python-only edition

This project is delivered as one Python file, `app.py`. It uses only Python's standard library, so no `pip install` is required. The website interface is embedded inside that file.

## Run it on Windows

1. Extract the ZIP.
2. Open the `VisionFix-Python` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. Run:

   ```bat
   python app.py
   ```

5. Open http://127.0.0.1:8000 in your browser.
6. To stop it, click the terminal and press Ctrl+C.

## Language support

- Python: uses Python's built-in AST syntax parser.
- C: uses `gcc` if installed.
- C++: uses `g++` if installed.
- Java: uses `javac` if installed; default source file is `Main.java`.
- JavaScript: uses `node --check` if Node.js is installed.

If a compiler/runtime is missing, VisionFix says so and uses a lightweight delimiter check. That fallback is not a full language parser. The app does not execute submitted code.

## Important honesty note

A syntax checker cannot guarantee a program is bug-free or logically correct. The interface is embedded in Python, but the browser still uses its built-in HTML/CSS/JavaScript rendering engine to display the page. No separate frontend files or frontend installation are needed.
