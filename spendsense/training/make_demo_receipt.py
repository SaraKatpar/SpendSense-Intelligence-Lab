"""Create a fictional receipt for a repeatable local OCR demonstration."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

root=Path(__file__).resolve().parents[1]
image=Image.new('RGB',(1000,760),'white')
draw=ImageDraw.Draw(image)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',34)
lines=['CORNER CAFE','FICTIONAL DEMO RECEIPT','Date: 2026-11-17','',
       'Lunch                         300.00','Tax                            50.00','',
       'TOTAL PKR                     350.00','Thank you']
for index,line in enumerate(lines):draw.text((60,45+index*65),line,font=font,fill='black')
image.save(root/'data/demo_receipt.png')
print('Created fictional demo receipt.')
