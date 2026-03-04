#!/usr/bin/env python3
import rospy
from sensor_msgs.msg import Imu

def imu_callback(msg):
    # 打印 IMU 数据
    rospy.loginfo("Received IMU data:")
    rospy.loginfo("Orientation - x: %.4f y: %.4f z: %.4f w: %.4f",
                  msg.orientation.x, msg.orientation.y, msg.orientation.z, msg.orientation.w)
    rospy.loginfo("Angular Velocity - x: %.4f y: %.4f z: %.4f",
                  msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z)
    rospy.loginfo("Linear Acceleration - x: %.4f y: %.4f z: %.4f",
                  msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z)

def imu_listener():
    rospy.init_node('imu_listener_node', anonymous=True)
    rospy.Subscriber('/imu/data', Imu, imu_callback)
    rospy.spin()

if __name__ == '__main__':
    imu_listener()
