from setuptools import setup, find_packages

setup(
    name="midifx",
    version="0.1.0",
    url="https://github.com/jvbalen/midifx",
    author="Jan Van Balen",
    author_email="janvanbalen@gmail.com",
    description="Approximately real-time MIDI manipulation for Python, macOS",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "pretty-midi>=0.2.9",
        "simplecoremidi>=0.3",
    ],
    extras_require={
        "test": ["pytest"],
    },
)
