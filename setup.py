from setuptools import setup

with open('digicampipe/VERSION') as f:
    __version__ = f.read().strip()


setup(
    name='digicampipe',
    version=__version__,
    packages=[
        'digicampipe',
        'digicampipe.io',
        'digicampipe.calib',
        'digicampipe.calib.camera',
        'digicampipe.utils',
        'digicampipe.visualization',
        'digicampipe.image',
        'digicampipe.instrument',
        'digicampipe.scripts',
    ],
    url='https://github.com/calispac/digicampipe',
    license='GNU GPL 3.0',
    author='Cyril Alispach',
    author_email='cyril.alispach@gmail.com',
    long_description=open('README.md').read(),
    description='A package for DigiCam pipeline',
    install_requires=[
        'numpy',
        'matplotlib',
        'scipy',
        'astropy',
        'h5py',
        'tqdm',
    ],
    tests_require=['pytest>=3.0.0'],
    setup_requires=['pytest-runner'],
    package_data={
        '': [
            'VERSION',
            'tests/resources/*',
            'tests/resources/stars_on_lid/*',
            'tests/resources/digicamtoy/*',
        ],
    },
    entry_points={
        'console_scripts': [
            'digicamview=digicampipe.scripts.digicamview:entry',
        ],
    }
)
