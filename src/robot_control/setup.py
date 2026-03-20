from setuptools import find_packages, setup

package_name = 'robot_control'

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
                'environment_setup = robot_control.environment_setup:main',
                'goal_controller = robot_control.goal_controller:main',
                'teleop_controller = robot_control.teleop_controller:main',
                'home_button_node = robot_control.home_button_node:main',
                'ros_image_to_raw = robot_control.ros_image_to_raw:main',
            ],
        },
)
