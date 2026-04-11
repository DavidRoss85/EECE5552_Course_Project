from setuptools import find_packages, setup

package_name = 'user_interface'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='abdul rahman',
    maintainer_email='mohammedabdulr.1@northeastern.edu',
    description='Pygame gaze overlay and VLA coordinate publisher for VisionGrip',
    license='Apache-2.0',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'gaze_overlay_node = user_interface.gaze_overlay_node:main',
            'dwell_vla_node    = user_interface.dwell_vla_node:main',
        ],
    },
)
