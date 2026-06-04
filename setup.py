from setuptools import setup

setup(
    name="parametric_scatter",
    version="1.0.0",
    description="Parametric Scatter Blender Add-on",
    py_modules=[
        "parametric_scatter",
        "scatter_core",
        "texture_processor",
        "operators",
        "ui_panel",
    ],
    packages=["parametric_scatter"],
    package_dir={"parametric_scatter": "."},
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "numpy>=1.24",
        "Pillow>=10.0",
    ],
)
