Documenting
===========

This documentation is a combination of manually-written parts and some auto-generated parts

It currently consists of:
    - `Sphinx` for generating HTML
    - `sphinx-apidoc` for generating doc pages from the python package

Generating Documentation
------------------------

The documentation consists of some graphical components which rely on the graphviz application which can be installed using the command ``sudo apt-get install graphviz``.

HTML
~~~~

To generate the HTML documentation and start a local documentation server, use the command::

    python tools/doc_server start_server

Adding the option ``--live`` to the above command will start a livereload server which automatically updates as the documentation is change.

LATEX / PDF
~~~~~~~~~~~

To generate a latex or pdf document, it is required to have latexmk installed. It can be installed with the command ``sudo apt-get install latexmk``.

A number of default fonts are also required which can be installed with the command ``sudo apt-get install texlive-fonts-recommended texlive-latex-recommended texlive-latex-extra``

Finally a pdf of the documentation can be generated using the command ``python tools/doc_server start_server`` and the pdf can then be found at ``docs/ANU Bushfire Initiative Drone Simulation Documentation.pdf``

Documentation Server
--------------------

.. toctree::
   :maxdepth: 4

   ../../auto_generated/documenting/documentation_server/modules.rst
