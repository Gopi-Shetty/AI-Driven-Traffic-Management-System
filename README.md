# AI-Driven-Traffic-Management-System
Traffic   signals can be a real pain sometimes. Imagine a situation where you have to wait for a red 
light at an intersection, and when you look around, there is no one coming from the other side. You 
still have to wait for the whole time. In addition, there are times that one lane is full of vehicles 
while the road that is perpendicular to it is almost empty, but the time of the lights remains the 
same. That seems quite ridiculous. That irritation was basically what made us decide to develop 
this project. A smarter way had to exist, we assumed, than the one we currently have. 
Actually, our answer is quite simple when you take it apart. With the help of cameras, we are able 
to monitor the traffic at intersections from all four directions. The cameras are connected to the 
software which is very simple in its work - it counts how many cars, bikes, and trucks are waiting 
at each road. As for the detection, we selected YOLOv5 because it performs well when recognizing 
vehicles. 
You have a choice of video sources - live feeds, pre-recorded footage, uploaded images, or 
whichever is convenient. The system takes care of everything and gives the vehicle counts for each 
approach. 
This is where the reason comes in. A longer green light is given to the direction that has many 
more vehicles than the others. It is as easy as that. We used Flask in the backend for the operations 
of the numbers and processing. Also, there is a web interface that shows the direction which 
currently has the green light, the countdown timers, and how everything cycles. 
The good thing about it is quite simple. Less time is spent at the lights without doing anything. 
Less fuel is burnt while the engine is idling. The air is cleaner. Traffic is flowing better overall. 
We have made it possible for the program to be flexible for different types of intersections so that 
cities would be able to deploy it in a realistic way. Compared to the old fixed-timer approach which 
has been around for a long time, this one actually reacts to the real situations rather than just 
following the schedule blindly. 
Still, there are some issues that we need to resolve, but it is certainly a step forward compared to 
what most places are   doing.

#Objectives: 
• Creating   an intelligent traffic management system capable of using YOLOv5 for locating 
and counting the vehicles in real-time from pictures, videos, or even a live webcam feed. 
• Based on the vehicle density at each junction, calculating how long the green signal should 
be shown and changing it dynamically. 
• Designing a web-based user interface with Flask for the traffic police to visualize, control 
and monitor the system. 
• Allowing a traffic management system to have three different methods of data input, i.e. 
image uploads, video uploads, and live webcam streams. 
• Assessing the system’s functionality through a set of metrics like detection precision, 
system response speed, computational resource usage, and the ease of user   interaction. 
