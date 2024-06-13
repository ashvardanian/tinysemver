from setuptools import setup

setup(
    name="tinysemver",
    version="1.0.0",
    author="Ash Vardanian",
    author_email="1983160+ashvardanian@users.noreply.github.com",
    description="Tiny Semantic Versioning (SemVer) library, that doesn't depend on 300K lines of JavaScript",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ashvardanian/affine-gaps",
    py_modules=["tinysemver"],
    install_requires=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    extras_require={"dev": ["pytest"]},
    entry_points={
        "console_scripts": [
            "affine-gaps=tinysemver:main",
        ],
    },
)
