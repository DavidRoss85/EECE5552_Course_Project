#This node performs object detection using a YOLO model on incoming RGB images
# and publishes detected objects along with annotated images.

# Math Imports:
import math
import numpy as np
import torch

# ROS2 Imports
import rclpy
from rclpy.node import Node
from std_msgs.msg import Header
from sensor_msgs.msg import Image
from geometry_msgs.msg import TransformStamped
from robot_interfaces.msg import DetectedItem, DetectedList


# OpenCV imports
import cv2      #pip3 install opencv-python
from cv_bridge import CvBridge

# YOLO library:
from ultralytics import YOLO #pip3 install typeguard ultralytics
#Ultralytics glitch when attempting to run. Use export to ensure proper import:
# export PYTHONPATH=</path/to/your/virtual/environment>/lib/python3.12/site-packages:$PYTHONPATH

# Configurations:
# from robot_common.config.ros_presets import STD_CFG
from intent_selection.config.detection_presets import DEFAULT_DETECTION_CONFIG
from intent_selection.config.yolo_presets import(
    DEFAULT_YOLO_CONFIG, 
    ComputePreference as CPU_Mode,
    YoloConfig,
    DetectionFilterMode as DetecMode
)

#######################################################################
#TEMP: MOVE THIS TO A CONFIG FILE LATER:
from enum import Enum

USING_GAZEBO = True

# Enum for various topics:
class TopicKey(str, Enum):
    RGB_FEED = '/input/camera_feed/rgb/'
    DEPTH_FEED = '/input/camera_feed/depth/'
    EYE_GAZE = '/input/eye_gaze/coords'
    VLA_INPUT = '/vla/input'
    VLA_OUTPUT = '/vla/output'
    MOVEIT_PLANNING = '/moveit/planning'
    OBJECT_DETECTIONS = '/intent_selection/detections'

from dataclasses import dataclass

# Data class for ros configurations
@dataclass(frozen=True)
class RosConfig:
    topic_full_view_rgb: str=TopicKey.RGB_FEED + 'full_view'
    topic_full_view_depth: str=TopicKey.DEPTH_FEED + 'full_view'
    topic_object_view_rgb: str=TopicKey.RGB_FEED + 'object_view'
    topic_object_view_depth: str=TopicKey.DEPTH_FEED + 'object_view'
    topic_eye_camera_rgb: str=TopicKey.RGB_FEED + 'eye_camera'
    topic_eye_gaze: str=TopicKey.EYE_GAZE
    topic_vla_input: str=TopicKey.VLA_INPUT
    topic_vla_output: str=TopicKey.VLA_OUTPUT
    topic_moveit_planning: str=TopicKey.MOVEIT_PLANNING
    detections_topic: str=TopicKey.OBJECT_DETECTIONS
    max_messages: int = 10
    sync_slop = 0.1

STD_CFG = RosConfig()
#############################################################################



class DetectionNode(Node):

    def __init__(self):
        super().__init__('detection_node')
        self.get_logger().info('Initializing Detection Node...')

        #Configurations:
        self._ros_config = STD_CFG
        self._yolo_config = DEFAULT_YOLO_CONFIG
        self._detection_config = DEFAULT_DETECTION_CONFIG
        
        self._pure_image = None    #Stores the pure image returned from the camera
        self._annotated_image = None   #Stores the image with boxes and identifiers
        self._detected_list = []   #List of DetectedItem messages to be published
        
        self._load_parameters()    #Load external parameters

        self._bridge = CvBridge()   # Initialize CV Bridge
        self.get_logger().info(f'CV Bridge loaded')

        self._process_device = self._select_device(self._yolo_config)   # Select processing device based on config
        self._model = YOLO(self._yolo_config.model.value)   # Load YOLO model

        self.get_logger().info(f'YOLO model loaded from: {self._yolo_config.model}')
        self.get_logger().info(f'Model confidence threshold set to: {self._yolo_config.confidence_threshold}')
        self.get_logger().info(f'Number of items in dataset: {len(self._model.names)}')

        try:
            # Subscriber
            self._image_sub = self.create_subscription(
                Image,
                self._ros_config.topic_object_view_rgb, #'Should reference the topic that the camera feed is published on',
                self._process_detections,
                self._ros_config.max_messages
            )
            self.get_logger().info(f'Subscribed to camera topic: {self._ros_config.topic_object_view_rgb}')
            
            # Publisher
            self._detection_pub = self.create_publisher(
                DetectedList,
                self._ros_config.detections_topic,
                self._ros_config.max_messages
            )
            self.get_logger().info(f'Publisher created on topic: {self._ros_config.detections_topic}')

            self.get_logger().info('Detection Node initialized and ready.')
        except Exception as e:
            self._handle_error(e,'__init__()','Failed to initialize Detection Node')
            self.destroy_node()
    
    #----------------------------------------------------------------------------------
    def _load_parameters(self):
        """Loads external parameters """
        #Enter code here to load parameters
        pass

    #----------------------------------------------------------------------------------
    def _select_device(self, config: YoloConfig) -> str:
        """Selects the device to process on based on the configuration."""
        if config.compute_preference == CPU_Mode.CPU_ONLY or \
            config.compute_preference == CPU_Mode.THROTTLED:
            return 'cpu'
        else:
             return 'cuda:0' if torch.cuda.is_available() else 'cpu'
    #----------------------------------------------------------------------------------
    def _process_detections(self,message:Image):

        rgb_image = message

        # Convert ros2 message to image:
        cv_image = self._bridge.imgmsg_to_cv2(rgb_image,self._detection_config.image_encoding)
        # Pass frame through model and return results:
        results = self._model(cv_image, verbose=False,device=self._process_device)[0]
        # Save original image:
        self._pure_image = cv_image
        self._annotated_image = cv_image.copy()   # Create a copy of the image to draw annotations on
        #Reset list:
        self._detected_list=[]
        
        
        # Get items and label if meet criteria
        if results.boxes:
            for box in results.boxes:
                if self._meets_critera(box):
                    # Get box coordinates:
                    x1,y1,x2,y2 = map(int,box.xyxy[0].tolist()) #Convert tensor to list
                    box_coords = [x1,y1,x2,y2]

                    xc,yc,w,h = map(int,box.xywh[0].tolist()) #Grab center of box
                    box_center = [xc,yc,w,h]

                    # Get box name:
                    item_name = self._model.names[int(box.cls)]    # Convert item index to name

                    # Create DetectedItem and add to list of detections:
                    detected_object = DetectedItem()
                    detected_object.xyxy = box_coords
                    detected_object.xywh = box_center
                    detected_object.name = item_name
                    detected_object.confidence = float(box.conf)
                    detected_object.index = int(box.cls)

                    # Add to list:
                    self._detected_list.append(detected_object)
                    
                    #These add boxes and labels to an annotated version of the image that can be published or shown in a feed:
                    # Add bounding box to annotated frame
                    self._annotated_image = self._add_bounding_box_to_image(
                        self._annotated_image,
                        xyxy = box_coords,
                        bgr = self._detection_config.bgr_box_color,
                        thickness= self._detection_config.line_thickness
                    )

                    # Add text with item's name/type to annotated frame
                    self._annotated_image=  self._add_text_to_image(
                        self._annotated_image,
                        x = box_coords[0],
                        y = box_coords[1],
                        text = item_name,
                        bgr = self._detection_config.bgr_font_color
                    )

        # Publish message if there are detections:
        if len(self._detected_list) > 0:
            pub_msg = DetectedList()
            pub_msg.header.stamp = self.get_clock().now().to_msg()
            pub_msg.item_list = self._detected_list
            pub_msg.image_raw = self._bridge.cv2_to_imgmsg(self._pure_image)
            pub_msg.image_annotated = self._bridge.cv2_to_imgmsg(self._annotated_image)
            self._publish_data(pub_msg)

        # Show feed if flag is set
        if self._detection_config.show_feed:
            cv2.imshow("Detections",self._annotated_image)
            cv2.waitKey(1)

    #----------------------------------------------------------------------------------
    def _meets_critera(self, box):
        """
        Criteria for identifying an object
        """
        # If confidence is over threshold
        if box.conf < self._yolo_config.confidence_threshold:
            return False
        
        # If there's a list of items to look for then filter by list
        if self._yolo_config.filter_mode == DetecMode.ALLOW\
        and self._model.names[int(box.cls)] not in self._yolo_config.target_classes:
            return False
        
        # Check the reject list:
        elif self._yolo_config.filter_mode == DetecMode.REJECT\
        and self._model.names[int(box.cls)] in self._yolo_config.ignore_classes:
            return False
        
        return True
    #----------------------------------------------------------------------------------
    def _add_bounding_box_to_image(self, image, xyxy=[0,0,0,0],bgr:tuple=(0,0,0),thickness:int=1):
        """Draw a rectangle at the given coordinates"""
        cv2.rectangle(
            image, 
            (xyxy[0],xyxy[1]),
            (xyxy[2],xyxy[3]),
            bgr,
            thickness
        )
        return image
    #----------------------------------------------------------------------------------
    def _add_text_to_image(self, image, x:int=0, y:int=0, text='',bgr:tuple=(0,0,0),font=cv2.FONT_HERSHEY_SIMPLEX,thickness=1):
        """Modify image with text at location"""
        cv2.putText(
            image,
            text,
            (x,y),
            font,
            self._detection_config.font_scale,
            bgr,
            thickness=thickness,
            lineType=cv2.LINE_AA
        )
        return image
 
    #----------------------------------------------------------------------------------
    def _publish_data(self,message:DetectedList):
        self._detection_pub.publish(message)

    #----------------------------------------------------------------------------------
    def _handle_error(self, error, function_name, custom_message=''):
        self.get_logger().error(f'Error in {function_name}: {str(error)}. {custom_message}')


def main(args=None):
    rclpy.init()
    detection_node = DetectionNode()
    rclpy.spin(detection_node)
    detection_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()