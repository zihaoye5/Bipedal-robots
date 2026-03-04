#include <assert.h>
#include <unistd.h>
#include <chrono>
#include <math.h>
#include <stdio.h>
#include <sys/stat.h>

#include "master_board_sdk/master_board_interface.h"
#include "master_board_sdk/defines.h"

#define N_SLAVES_CONTROLED 6

int main(int argc, char **argv)
{
    if(argc != 2)
    {
        throw std::runtime_error("Please provide the interface name "
                                 "(i.e. using 'ifconfig' on linux");
    }

	int cpt = 0;
	double dt = 0.001;
	double t = 0;
	double kp = 3;
	double kd = 0.1;
	double iq_sat = 4.0;
	double freq = 0.2;
	double amplitude = 20*M_PI;
	// double amplitude = 20;
	double init_pos[N_SLAVES * 2] = {0};
	int state = 0;

	nice(-20); //give the process a high priority
	printf("-- Main --\n");
	MasterBoardInterface robot_if(argv[1]);
	robot_if.Init();
	//Initialisation, send the init commands
	for (int i = 0; i < N_SLAVES_CONTROLED; i++)
	{
		robot_if.motor_drivers[i].motor1->SetCurrentReference(0);
		robot_if.motor_drivers[i].motor2->SetCurrentReference(0);
		robot_if.motor_drivers[i].motor1->Enable();
		robot_if.motor_drivers[i].motor2->Enable();
		
		// Set the gains for the PD controller running on the cards.
		robot_if.motor_drivers[i].motor1->set_kp(kp);
		robot_if.motor_drivers[i].motor2->set_kp(kp);
		robot_if.motor_drivers[i].motor1->set_kd(kd);
		robot_if.motor_drivers[i].motor2->set_kd(kd);

		// Set the maximum current controlled by the card.
		robot_if.motor_drivers[i].motor1->set_current_sat(iq_sat);
		robot_if.motor_drivers[i].motor2->set_current_sat(iq_sat);
		
		robot_if.motor_drivers[i].EnablePositionRolloverError();
		robot_if.motor_drivers[i].SetTimeout(5);
		robot_if.motor_drivers[i].Enable();
	}

	std::chrono::time_point<std::chrono::system_clock> last = std::chrono::system_clock::now();
	while (!robot_if.IsTimeout() && !robot_if.IsAckMsgReceived()) {
		if (((std::chrono::duration<double>)(std::chrono::system_clock::now() - last)).count() > dt)
		{
			last = std::chrono::system_clock::now();
			robot_if.SendInit();
		}
	}

	if (robot_if.IsTimeout())
	{
		printf("Timeout while waiting for ack.\n");
	}

	while (!robot_if.IsTimeout())
	{
		if (((std::chrono::duration<double>)(std::chrono::system_clock::now() - last)).count() > dt)
		{
			last = std::chrono::system_clock::now(); //last+dt would be better
			cpt++;
			t += dt;
			robot_if.ParseSensorData(); // This will read the last incomming packet and update all sensor fields.
			switch (state)
			{
			case 0: //check the end of calibration (are the all controlled motor enabled and ready?)
				state = 1;
				for (int i = 0; i < N_SLAVES_CONTROLED * 2; i++)
				{
					if (!robot_if.motor_drivers[i / 2].is_connected) continue; // ignoring the motors of a disconnected slave

					if (!(robot_if.motors[i].IsEnabled() && robot_if.motors[i].IsReady()))
					{
						state = 0;
					}
					init_pos[i] = robot_if.motors[i].GetPosition(); //initial position

					// Use the current state as target for the PD controller.
					robot_if.motors[i].SetCurrentReference(0.);
					robot_if.motors[i].SetPositionReference(init_pos[i]);
					robot_if.motors[i].SetVelocityReference(0.);

					t = 0;	//to start sin at 0
				}
				break;
			// case 1:
			// 	//closed loop, position
			// 	for (int i = 0; i < N_SLAVES_CONTROLED * 2; i++)
			// 	{
			// 		if (i % 2 == 0)
			// 		{
			// 			if (!robot_if.motor_drivers[i / 2].is_connected) continue; // ignoring the motors of a disconnected slave
 
			// 			// making sure that the transaction with the corresponding µdriver board succeeded
			// 			if (robot_if.motor_drivers[i / 2].error_code == 0xf)
			// 			{
			// 				//printf("Transaction with SPI%d failed\n", i / 2);
			// 				continue; //user should decide what to do in that case, here we ignore that motor
			// 			}
			// 		}

			// 		// if (robot_if.motors[i].IsEnabled())
			// 		// {
			// 		// 	double ref = init_pos[i] + amplitude * sin(2 * M_PI * freq * t);
			// 		// 	double v_ref = 2. * M_PI * freq * amplitude * cos(2 * M_PI * freq * t);

			// 		// 	robot_if.motors[i].SetCurrentReference(0.);
			// 		// 	robot_if.motors[i].SetPositionReference(ref);
			// 		// 	robot_if.motors[i].SetVelocityReference(v_ref);
			// 		// }
			// 		if (robot_if.motors[i].IsEnabled())
			// 		{
			// 			double v_const = 2.0 * M_PI;  // 约等于 6.28 rad/s
			// 			double ref = init_pos[i] + v_const * t;
			// 			double v_ref = v_const;

			// 			robot_if.motors[i].SetCurrentReference(0.);
			// 			robot_if.motors[i].SetPositionReference(ref);
			// 			robot_if.motors[i].SetVelocityReference(v_ref);
					

			// 		}

			// 	}
			// 	break;

			case 1:
			// closed loop, direct current control
			for (int i = 0; i < N_SLAVES_CONTROLED * 2; i++)
			{
				if (i % 2 == 0)
				{
					if (!robot_if.motor_drivers[i / 2].is_connected)
						continue; // 忽略断线的从板
		
					// 检查对应的µdriver板卡的交易是否成功
					if (robot_if.motor_drivers[i / 2].error_code == 0xf)
					{
						continue; // 如果出错，忽略该电机
					}
				}
		
				if (robot_if.motors[i].IsEnabled())
				{
					double cur = 1.0;  // 设定电流为 1A
					robot_if.motors[i].SetCurrentReference(cur);
					
					// 为避免位置/速度控制的影响，将位置保持为初始值，速度设为0
					robot_if.motors[i].SetPositionReference(init_pos[i]);
					robot_if.motors[i].SetVelocityReference(0.);
				}
			}
			break;
					


			}
			if (cpt % 100 == 0)
			{
				printf("\33[H\33[2J"); //clear screen
				robot_if.PrintIMU();
				robot_if.PrintADC();
				robot_if.PrintMotors();
				robot_if.PrintMotorDrivers();
				robot_if.PrintStats();
				fflush(stdout);
				 

			}
			robot_if.SendCommand(); //This will send the command packet
		}
		else
		{
			std::this_thread::yield();
		}
	}
        printf("Masterboard timeout detected. Either the masterboard has been shut down or there has been a connection issue with the cable/wifi.\n");
	return 0;
}
