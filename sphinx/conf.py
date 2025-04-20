# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'SideKick'
copyright = '(C) 2025 LANNOCC'
author = 'LANNOCC'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc', 'autoapi.extension', 'sphinx.ext.viewcode']
autodoc_typehints = 'description'
autoapi_dirs = ['../sk']

templates_path = ['templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_static_path = ['static']
#html_logo = 'sidekick.png'

#html_theme = 'sphinx_book_theme'
#html_theme_options = {
#        'repository_url': 'https://make.lanno.cc/source/sidekick',
#        'use_repository_button': True,
#}
html_theme = 'piccolo_theme'
html_css_files = ['lannocc.css']

