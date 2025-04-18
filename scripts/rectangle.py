import pygame

# Initialize Pygame
pygame.init()

# Screen dimensions
#screen_width = 800
#screen_height = 600
info = pygame.display.Info()
screen_width = info.current_w
screen_height = info.current_h

# Create the screen
flags = pygame.FULLSCREEN
screen = pygame.display.set_mode((screen_width, screen_height), flags)

# Set the window title
pygame.display.set_caption("Transparent Rectangle")

# Rectangle properties
rect_width = 200
rect_height = 150
rect_color = (0, 0, 255)  # Blue
transparency = 128  # Range 0-255 (0 is fully transparent, 255 is fully opaque)
rect_x = (screen_width - rect_width) // 2  # Center horizontally
rect_y = (screen_height - rect_height) // 2  # Center vertically

# Game loop
running = True
while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Clear the screen (fill with black, for example)
    screen.fill((0, 255, 0))

    # Create a surface for the rectangle
    rect_surface = pygame.Surface((rect_width, rect_height), pygame.SRCALPHA)  # SRCALPHA for transparency
    rect_surface.fill((rect_color[0], rect_color[1], rect_color[2], transparency))  # Fill with color and transparency

    # Draw the transparent rectangle onto the screen
    screen.blit(rect_surface, (rect_x, rect_y))

    # Update the display
    #pygame.display.flip()

    #pygame.display.update([0,0,100,100])

# Quit Pygame
pygame.quit()

