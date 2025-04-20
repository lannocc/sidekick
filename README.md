# SideKick

SideKick leverages AI to do some things...

## Getting Started

### Required Software

* Python (using 3.13) with pip installed

### Installation Steps

If you haven't already, first get the code:

1. `git clone ssh://make.lanno.cc/source/sidekick`

#### A. Python Setup

1. `cd sidekick`
2. `python -m venv venv`
3. `source venv/bin/activate`
4. `pip install .`

### Building Documentation

We use Sphinx for generating documentation:

```bash
cd sidekick
sphinx-apidoc -o sphinx sk
make html
```

