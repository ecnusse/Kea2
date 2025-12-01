# Documentation for developers

We are looking for maintainers and contributors for Kea2. If you have interest in maintaining Kea2, don't hesitate to contact us.

## Installation

1. Clone `Kea2` into your workspace.

```bash
git clone git@github.com:ecnusse/Kea2.git
cd Kea2
```

2. Setup the python virtual environment with `uv`.

> [uv](https://github.com/astral-sh/uv) is a extremely fast python package and project manager. We use `uv` to create a python virtual environment for Kea2 to avoid any dependency issues or conflicts with your existing python environment.
`uv` is similar to `virtualenv` but much more powerful.
Of course, you can also setup Kea2 in your [global environment](https://github.com/ecnusse/Kea2/tree/dev?tab=readme-ov-file#appendix-install-kea2-in-a-global-environment).

```bash
pip install --upgrade pip
pip install uv
uv sync
```

> MacOS users may have trouble with global pip install. In such cases, they can use `brew`.
```bash
# For macOS users
brew install uv
uv sync
```

3. Activate virtual environment

- Linux and macOS
```bash
source .venv/bin/activate
```

- Windows cmd
```cmd
\.venv\Scripts\activate.bat
```

- Windows powershell
```powershell
\.venv\Scripts\activate.ps1
```

## Fastbot Server

Kea2 use a customized version of Fastbot. Which is open sourced at [ecnusse/Fastbot-Android](https://github.com/ecnusse/Fastbot_Android).