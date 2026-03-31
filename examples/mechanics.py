from typing import Annotated

mass: Annotated[float, "kg"] = 5.0
acceleration: Annotated[float, "m/s^2"] = 9.81

spring_k = 200.0        # N/m
displacement = 0.05     # m

force = mass * acceleration
spring_force = spring_k * displacement

velocity: Annotated[float, "m/s"] = 20.0
time: Annotated[float, "s"] = 4.0
distance = velocity * time

kinetic_energy = mass * velocity ** 2

# this line is wrong on purpose
bad = force + velocity
