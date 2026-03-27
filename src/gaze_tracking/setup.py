from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'gaze_tracking'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='abdul rahman',
    maintainer_email='mohammedabdulr.1@northeastern.edu',
    description='Eye gaze tracking for VisionGrip',
    license='Apache-2.0',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'gaze_tracking_node = gaze_tracking.gaze_tracking_node:main',
        ],
    },
)
