mass: "kg" = 5.0
acceleration: "m/s^2" = 9.81

spring_k = 200.0        # N/m
displacement = 0.05     # m

force = mass * acceleration
spring_force = spring_k * displacement

velocity: "m/s" = 20.0
time: "s" = 4.0
distance = velocity * time

kinetic_energy = mass * velocity ** 2

# this line is wrong on purpose — adding incompatible units
bad = force + velocity
