from distutils.log import error
import rclpy
import os
import sys
import select
import time

from geometry_msgs.msg import Twist
from rclpy.qos import QoSProfile

# If we are on Windows, we need to use msvcrt
if os.name == 'nt':
    import msvcrt
# Otherwise, we can use termios and tty
else:
    import termios
    import tty
    

# Min and Max Velocities for TurtleBot3 Waffle
WAFFLE_MAX_LIN_VEL = 0.26
WAFFLE_MAX_ANG_VEL = 1.82

# How much we increase our velocity by each time
LIN_VEL_STEP_SIZE = 0.2
ANG_VEL_STEP_SIZE = 0.628

# Get the model of the turtlebot3
# Should always be waffle_pi, but this is a fallback
TURTLEBOT3_MODEL = os.environ['TURTLEBOT3_MODEL']

# Print the current velocity of the turtlebot3 for debugging purposes.
def print_values(target_linear_velocity, target_angular_velocity):
    print('currently:\tlinear velocity {0}\t angular velocity {1} '.format(
        target_linear_velocity,
        target_angular_velocity))

# Checks if the input is within the given range.
# If not, it returns the closest value to the given range.
# i.e. if min is -1 and input is -2, it will return -1
# and if max is 1 and input is 2, it will return 1
# else it will return the input
def constraint(input, min, max):
    if input < min:
        input = min
    elif input > max:
        input = max
    else:
        input = input
    return input

# Check if the turtlebot3 is capable of moving at the given velocity.
# Important: This function makes it so we don't possibly damage turtlebot3.
def check_limit(type_of_velocity, velocity_value, model="waffle"):
    if(type_of_velocity == "angular"):
        return constraint(velocity_value, -WAFFLE_MAX_ANG_VEL, WAFFLE_MAX_ANG_VEL)
    elif(type_of_velocity == "linear"):
        return constraint(velocity_value, -WAFFLE_MAX_LIN_VEL, WAFFLE_MAX_LIN_VEL)
    else:
        error("Unknown type of velocity! Please use 'linear' or 'angular'.")

# This function is used to help us prevent the robot from 
# moving at speeds that are too fast or too slow.
def make_simple_profile(output, input, slop):
    if input > output:
        output = min(input, output + slop)
    elif input < output:
        output = max(input, output - slop)
    else:
        output = input

    return output    
    

def main():
    settings = None
    if os.name != 'nt':
        settings = termios.tcgetattr(sys.stdin)

    # rscply initialization
    # this is how we use the ROS2 API
    # to move turtlebot3
    rclpy.init()
    qos = QoSProfile(depth=10)
    node = rclpy.create_node('teleop_keyboard')
    pub = node.create_publisher(Twist, 'cmd_vel', qos)

    # Variables for the turtlebot3
    target_linear_velocity = 0.0
    target_angular_velocity = 0.0
    control_linear_velocity = 0.0
    control_angular_velocity = 0.0
    
    
    # A simple way to reset the linear and angular velocities to 0
    # This is useful when we want to stop the robot or when we want to 
    # make the robot move from a left to a right.
    # If we don't do this the robot will go from right to straight
    # instead of right to left. This is caused by the fact that -.628 + .628 = 0
    # instead of .628. 
    def reset_velocity(velocity_type):
        temp_twist = Twist()
        
        if(velocity_type == "linear"):
            temp_twist.linear.x = 0.0
        elif(velocity_type == "angular"):
            temp_twist.angular.z = 0.0
        elif(velocity_type == "both"):
            temp_twist.linear.x = 0.0
            temp_twist.angular.z = 0.0
        else:
            error("Unknown type of velocity! Please use 'linear' or 'angular'.")
        pub.publish(temp_twist)
    
    # List of commands that turtlebot3 will execute.
    # List of Available Commands:
    # ~ Straight (Go Straight)
    # ~ Back (Go straight backwards)
    # ~ Left
    # ~ Right
    # ~ Stop (Stop all velocities)
    commands = ["Straight", "Left", "Right", "Left", "Back", "Stop"]
    
    try:
        for command in commands:
            
            if command == "Straight":
                target_linear_velocity =\
                    check_limit("linear", target_linear_velocity + LIN_VEL_STEP_SIZE)
                print_values(target_linear_velocity, target_angular_velocity)
            
            elif command == "Back":
                target_linear_velocity = 0.0
                control_linear_velocity = 0.0
                target_angular_velocity = 0.0
                control_angular_velocity = 0.0
                target_linear_velocity =\
                    check_limit("linear", target_linear_velocity - LIN_VEL_STEP_SIZE)
                print_values(target_linear_velocity, target_angular_velocity)
            
            elif command == "Left":
                target_angular_velocity = 0.0
                control_angular_velocity = 0.0
                target_angular_velocity =\
                    check_limit("angular", target_angular_velocity + ANG_VEL_STEP_SIZE)
                print_values(target_linear_velocity, target_angular_velocity)
            
            elif command == "Right":
                target_angular_velocity = 0.0
                control_angular_velocity = 0.0
                target_angular_velocity =\
                    check_limit("angular", target_angular_velocity - ANG_VEL_STEP_SIZE)
                print_values(target_linear_velocity, target_angular_velocity)
            
            elif command == "Stop":
                target_linear_velocity = 0.0
                control_linear_velocity = 0.0
                target_angular_velocity = 0.0
                control_angular_velocity = 0.0
                print_values(target_linear_velocity, target_angular_velocity)
                
            else:
                print("Unknown command: " + command)
                
            # Twist is a message type in geometry_msgs.
            # This message type is a twist with linear and angular velocities.
            # This is how we are able to manipulate turtlebot3's velocities.
            # i.e. move forward, backward, turn left, turn right, etc.
            twist = Twist()
            
            # Use simple profile for linear velocity to
            # check before attempting to move the robot
            control_linear_velocity = make_simple_profile(
                control_linear_velocity,
                target_linear_velocity,
                (LIN_VEL_STEP_SIZE / 2.0)
            )
            
            # Update linear velocity.
            twist.linear.x = control_linear_velocity
            twist.linear.y = 0.0
            twist.linear.z = 0.0
            
            # Use simple profile for angular velocity to
            # check before attempting to turn the robot
            control_angular_velocity = make_simple_profile(
                control_angular_velocity,
                target_angular_velocity,
                (ANG_VEL_STEP_SIZE / 2.0)
            )
            
            # Update angular velocity
            twist.angular.x = 0.0
            twist.angular.y = 0.0
            twist.angular.z = control_angular_velocity
            
            # Send the new velocities to turtlebot3 via the publisher.
            # using twist.
            pub.publish(twist)
            
            # time.sleep so that the robot can have time to move
            time.sleep(5)
        
    except Exception as e:
        # Exit the program cleanly
        print(e)
          
    finally:
        # Stop the robot when we are done
        twist = Twist()
        twist.linear.x = 0.0
        twist.linear.y = 0.0
        twist.linear.z = 0.0

        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = 0.0

        pub.publish(twist)

        if os.name != 'nt':
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        
            
    
        
if __name__ == "__main__":
    main()    

