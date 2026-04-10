import fitz
from PIL import Image
import io

path = r"C:\Users\User\Desktop\Вент проекты\Проект ОВ - Пожарное депо от 11.03.26-17-20.pdf"
doc = fitz.open(path)

for i in range(1, min(4, len(doc))):
    page = doc[i]
    mat = fitz.Matrix(1.5, 1.5)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    img.save(fr"C:\vent_app\project_root\page_{i+1}.png")
    print(f"Сохранено page_{i+1}.png")

doc.close()