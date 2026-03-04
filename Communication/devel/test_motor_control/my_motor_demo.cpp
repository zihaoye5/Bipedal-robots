#include "master_board_sdk/master_board_interface.h"
#include <chrono>
#include <thread>
#include <iostream>

int main() {
    MasterBoardInterface board("enx6c1ff7146b96");  // 网卡名称
    board.Init();

    std::cout << "Waiting for communication with the board..." << std::endl;

    // 等待通信建立
    for (int i = 0; i < 1000 && !board.IsAckMsgReceived(); ++i) {
        board.SendCommand();  // 发送命令
        board.ParseSensorData();  // 解析传感器数据
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }

    if (!board.IsAckMsgReceived()) {
        std::cerr << "Failed to connect to board!" << std::endl;
        return 1;
    }

    std::cout << "Connected! Sending current to motor 0..." << std::endl;

    board.GetMotor(0)->Enable();  // 启动 motor 0
    board.GetMotor(0)->set_current(0.4);  // 设置电流为 0.5A

    for (int i = 0; i < 2000; ++i) {
        board.SendCommand();  // 发送命令
        board.ParseSensorData();  // 解析传感器数据

        float pos = board.GetMotor(0)->get_position();  // 获取 motor 0 的位置
        float vel = board.GetMotor(0)->get_velocity();  // 获取 motor 0 的速度
        std::cout << "pos: " << pos << "  vel: " << vel << std::endl;

        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }

    std::cout << "Done." << std::endl;
    return 0;
}
