"""TODO Docstring."""

import glob
import logging
import os
import subprocess

import typer
from livereload import Server, shell

_LOG = logging.getLogger(__name__)
app = typer.Typer()


@app.command()
def make_documentation() -> None:
    """Make documentation."""
    script_location = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_location + "/../")

    subprocess.run(
        [
            "sphinx-apidoc",
            "-f",
            "-o",
            "docs/source/auto_generated/documenting/documentation_server",
            "tools",
        ],
        check=True,
    )

    applications = ["bushfire_drone_simulation"]
    for application in applications:
        # Generate sphinx auto documentation
        subprocess.run(
            [
                "sphinx-apidoc",
                "-f",
                "-o",
                "docs/source/auto_generated/application/" + application,
                application + "/src/" + application,
            ],
            check=True,
        )

        files = glob.glob(f"{application}/src/{application}/**/*.py", recursive=True)
        previous_text = ""
        with open(
            f"docs/source/auto_generated/application/{application}/modules.rst",
            "r",
            encoding="utf8",
        ) as application_rst:
            previous_text = application_rst.read().replace("=", "-")

        with open(
            f"docs/source/auto_generated/application/{application}/modules.rst",
            "w",
            encoding="utf8",
        ) as application_rst:
            # Move readme into sphinx docs
            with open(f"{application}/README.rst", encoding="utf8") as readme:
                application_rst.write(readme.read())

            application_rst.write("\n\n")

            application_rst.write(previous_text)

            # Generate class inheritance trees
            application_rst.write("\n\nClasses\n-------\n")
            display_files = []
            for module_file in files:
                module_file = (
                    module_file.strip("py")
                    .strip(".")
                    .replace(f"{application}/src/", "")
                    .replace("/", ".")
                    .replace("\\", ".")
                )
                if not module_file.endswith("_"):
                    display_files.append(module_file)
            application_rst.write(f".. inheritance-diagram:: {' '.join(display_files)}\n")
            application_rst.write("  :parts: 1\n\n")

    os.chdir(os.getcwd() + "/docs/")
    if os.name == "nt":  # Running on a windows maching
        subprocess.run(["make.bat", "clean"], check=True)
        subprocess.run(["make.bat", "html"], check=True)
    else:
        subprocess.run(["make", "clean"], check=True)
        subprocess.run(["make", "html"], check=True)
    os.chdir(script_location + "/../")


@app.command()
def start_server(host: str = "localhost", port: str = "8000", live: bool = False) -> None:
    """Start server for documentation."""
    make_documentation()
    server = Server()
    if live:
        for filename in os.listdir("docs/source"):
            if not filename.startswith("_") and filename != "auto_generated":
                server.watch(
                    os.getcwd() + f"/docs/source/{filename}",
                    shell("python tools/doc_server.py make-documentation"),
                )
        server.watch(
            os.getcwd() + "/bushfire_drone_simulation",
            shell("python tools/doc_server.py make-documentation"),
        )
        server.watch(os.getcwd() + "/tools", shell("python tools/doc_server.py make-documentation"))
    server.serve(root="docs/build/html", host=host, port=port)


@app.command()
def make_pdf() -> None:
    """Make a pdf version of the documentation."""
    script_location = os.path.dirname(os.path.abspath(__file__))
    make_documentation()
    os.chdir(os.getcwd() + "/docs/")
    subprocess.run(["make", "latexpdf"], check=True)
    subprocess.run(
        [
            "cp",
            "build/latex/anubushfireinitiativedronesimulation.pdf",
            "ANU Bushfire Initiative Drone Simulation Documentation.pdf",
        ],
        check=True,
    )
    os.chdir(script_location + "/../")


if __name__ == "__main__":
    app()
