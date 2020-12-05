"""Configuration file for Sphinx documentation builder."""

# pylint: disable=C0103

# For a full of configuration options see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with auto doc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
import os
import sys

sys.path.insert(0, os.path.abspath("../../bushfire_drone_simulation/"))
sys.path.insert(0, os.path.abspath("../../bushfire_drone_simulation/src/"))
sys.path.insert(0, os.path.abspath("../../bushfire_drone_simulation/src/bushfire_drone_simulation"))
sys.path.insert(0, os.path.abspath("../../tools/"))
sys.path.insert(0, os.path.abspath(".."))


# -- Project information -----------------------------------------------------

project = "ANU Bushfire Initiative Drone Simulation"
# pylint: disable=redefined-builtin
copyright = "2020, Ryan Stocks and Elise Palethorpe, Australian National University"
author = "Ryan Stocks and Elise Palethorpe, Australian National University"

# The full version, including alpha/beta/rc tags
release = "dev"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx_rtd_theme",
    "sphinx.ext.autodoc",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.graphviz",
    "sphinx.ext.napoleon",
    "sphinx.ext.doctest",
    "sphinx_autodoc_typehints",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

napoleon_google_docstring = True
napoleon_use_param = True

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

html_logo = "drone_simulation_logo.png"
html_favicon = "drone_simulation_logo.png"

html_theme_options = {"logo_only": False}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
