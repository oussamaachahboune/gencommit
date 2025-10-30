from setuptools import setup

setup(
    name="gencommit",
    version="1.0.0",
    py_modules=["gencommit"],
    install_requires=["requests"],
    entry_points={
        "console_scripts": [
            "gencommit=gencommit:main",
        ],
    },
    author="ACHAHBOUNE Oussama",
    description="AI-powered Git commit message generator using Anthropic Claude.",
    python_requires=">=3.8",
)
