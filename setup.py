from setuptools import setup, find_packages

setup(
    name="AutoCYPAmber",
    version="1.0.0",
    author="Ziyan Zhuang, Qianyu Zhao",
    description="Autonomous Orchestration for High-Fidelity Cytochrome P450 and Ligand MD Simulations",
    packages=find_packages(include=["acypa", "acypa.*"]),
    include_package_data=True,
    package_data={
        "acypa": [
            "data/heme_params/*/*.mol2",
            "data/heme_params/*/*.frcmod",
        ]
    },
    install_requires=[
        "numpy",
        "scipy",
        "matplotlib",
        "PyYAML",
        "pyscf"
    ],
    classifiers=[
        "Intended Audience :: Science/Research",
        "License :: Free for non-commercial use",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Topic :: Scientific/Engineering :: Chemistry",
    ],
    python_requires='>=3.8',
)
