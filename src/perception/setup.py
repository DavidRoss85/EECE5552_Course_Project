from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'perception'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='david-ross',
    maintainer_email='ross.d2@northeastern.edu',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'camera_streamer = perception.nodes.generic_camera_streamer:main',
            'camera_viewer = perception.nodes.generic_camera_viewer:main',
            'detection_node = perception.detection_node:main',
            'object_localizer_node = perception.object_localizer_node:main',
            'vla_detector = perception.vla_detector:main',
        ],
    },
)
