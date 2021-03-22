"""
setup.py for using pip
"""
import setuptools

with open("README.md", "r", encoding="utf-8") as readme_file:
    long_description = readme_file.read()

setuptools.setup(
    name="prometheus-exporter",
    version="1.0.0",
    author="Jim Ramsay, Aviel Yosef",
    author_email="jramsay@redhat.com, Avielyo10@gmail.com",
    description="Process Interrogator for OpenShift",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # url="https://github.com/Avielyo10/jinja2-tools.git", #TODO move to new repo?
    packages=setuptools.find_packages(),
    install_requires=[
        'Click',
        'PyYAML',
        'requests',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.5',
    entry_points='''
        [console_scripts]
        prome=prometheus.cli:main
    ''',
)