from setuptools import find_packages, setup

setup(
    name="metuber",
    version="2.0.0",
    description="Real-time webcam effects, virtual camera, and Twitch bot tooling for streamers.",
    author="Victor",
    packages=find_packages(exclude=["Transcripts*"]),
    include_package_data=True,
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "metuber-echo-bot=twitch_bots.echo_bot.__main__:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
