#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Imu

def imu_callback(msg):
    rospy.loginfo("IMU 数据接收成功")
    rospy.loginfo(f"Orientation: x={msg.orientation.x:.3f}, y={msg.orientation.y:.3f}, z={msg.orientation.z:.3f}, w={msg.orientation.w:.3f}")
    rospy.loginfo(f"Angular velocity: x={msg.angular_velocity.x:.3f}, y={msg.angular_velocity.y:.3f}, z={msg.angular_velocity.z:.3f}")
    rospy.loginfo(f"Linear acceleration: x={msg.linear_acceleration.x:.3f}, y={msg.linear_acceleration.y:.3f}, z={msg.linear_acceleration.z:.3f}")

def main():
    rospy.init_node('ros_mujoco_bridge')
    rospy.Subscriber('/imu/data', Imu, imu_callback)
    rospy.loginfo("已启动 ros_mujoco_bridge 节点，等待 IMU 数据...")
    rospy.spin()

if __name__ == '__main__':
    main()
