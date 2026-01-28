#!/usr/bin/env python3
"""Generate icons for the desktop app from logo.png"""
from PIL import Image
import os

def main():
    icons_dir = 'desktop-app/src-tauri/icons'
    source = os.path.join(icons_dir, 'icon.png')
    
    print(f"Loading image from: {source}")
    img = Image.open(source).convert('RGBA')
    print(f"Image size: {img.size}")
    
    # Create PNG icons
    sizes = [(32, '32x32.png'), (128, '128x128.png'), (256, '128x128@2x.png'), (512, '512x512.png')]
    for size, name in sizes:
        resized = img.resize((size, size), Image.LANCZOS)
        resized.save(os.path.join(icons_dir, name), 'PNG')
        print(f'Created {name}')
    
    # Create ICO for Windows
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_images = [img.resize(size, Image.LANCZOS) for size in ico_sizes]
    ico_images[0].save(os.path.join(icons_dir, 'icon.ico'), format='ICO', sizes=ico_sizes)
    print('Created icon.ico')
    
    # Create iconset for macOS
    iconset_dir = os.path.join(icons_dir, 'icon.iconset')
    os.makedirs(iconset_dir, exist_ok=True)
    
    iconset_sizes = [
        (16, 'icon_16x16.png'), (32, 'icon_16x16@2x.png'),
        (32, 'icon_32x32.png'), (64, 'icon_32x32@2x.png'),
        (128, 'icon_128x128.png'), (256, 'icon_128x128@2x.png'),
        (256, 'icon_256x256.png'), (512, 'icon_256x256@2x.png'),
        (512, 'icon_512x512.png'), (1024, 'icon_512x512@2x.png'),
    ]
    
    for size, name in iconset_sizes:
        resized = img.resize((size, size), Image.LANCZOS)
        resized.save(os.path.join(iconset_dir, name), 'PNG')
    
    print('Created iconset files')
    print('Done!')

if __name__ == '__main__':
    main()
