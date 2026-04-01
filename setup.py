from setuptools import setup
from catkin_pkg.python_setup import generate_distutils_setup

d = generate_distutils_setup(
    packages=["logdiag", "logdiag.llm_engine", "logdiag.tools",
              "logdiag.diagnosis", "logdiag.conversation"],
    package_dir={"": "src"},
)

setup(**d)
