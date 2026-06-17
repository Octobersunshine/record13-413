from pathlib import Path
from PIL import Image
from converter import convert_image, _has_transparency


def create_test_images():
    """创建各种带透明度的测试图片"""
    Path("./test_images").mkdir(exist_ok=True)

    # 1. RGBA 模式 - 半透明红色方块
    img_rgba = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    img_rgba.save("./test_images/test_rgba.png")
    print(f"[+] Created RGBA: {img_rgba.mode}")

    # 2. LA 模式 - 灰度 + Alpha
    img_la = Image.new("LA", (100, 100), (128, 128))
    img_la.save("./test_images/test_la.png")
    print(f"[+] Created LA: {img_la.mode}")

    # 3. P 调色板模式 + 透明度（通过 transparency 信息）
    img_rgba2 = Image.new("RGBA", (100, 100), (0, 255, 0, 128))
    img_p = img_rgba2.convert("P", palette=Image.ADAPTIVE, colors=256)
    img_p.save("./test_images/test_p.png")
    print(f"[+] Created P: {img_p.mode}, has transparency info: {img_p.info.get('transparency') is not None}")

    # 4. 普通 RGB 模式（无透明）
    img_rgb = Image.new("RGB", (100, 100), (0, 0, 255))
    img_rgb.save("./test_images/test_rgb.png")
    print(f"[+] Created RGB: {img_rgb.mode}")

    return [
        "./test_images/test_rgba.png",
        "./test_images/test_la.png",
        "./test_images/test_p.png",
        "./test_images/test_rgb.png",
    ]


def test_transparency_detection(paths):
    """测试透明度检测函数"""
    print("\n=== Transparency Detection Test ===")
    for p in paths:
        with Image.open(p) as img:
            has_t = _has_transparency(img)
            print(f"  {Path(p).name}: mode={img.mode}, has_transparency={has_t}")


def test_conversion_to_jpg(paths):
    """测试转换为 JPG，验证背景为白色而非黑色"""
    print("\n=== PNG -> JPG Conversion Test ===")
    for p in paths:
        out = convert_image(p, target_format="jpg", quality=90)
        with Image.open(out) as img:
            pixels = list(img.getdata())
            # 检查角落像素是否为白色 (255,255,255) - 半透明区域应该被白底合成
            corner = pixels[0]
            print(f"  {Path(p).name} -> {Path(out).name}: mode={img.mode}, corner_pixel={corner}")
            # 对于带透明度的图片，角落应该是白色（因为整体是半透明色+白底）
            # 对于不透明的RGB，角落应该是原色
            if "rgb.png" in p:
                # JPEG 有损压缩，允许 ±1 误差
                r, g, b = corner
                assert abs(r - 0) <= 1 and abs(g - 0) <= 1 and abs(b - 255) <= 1, f"RGB should remain blue, got {corner}"
            else:
                # 半透明红+白底 = 粉红ish (255, 128, 128) / 半透明绿+白底 = (128, 255, 128)
                # 灰度半透明+白底 = 浅灰
                r, g, b = corner
                # 关键断言：绝对不能是黑色 (0,0,0)
                assert corner != (0, 0, 0), f"BUG! Transparent background turned BLACK: {corner}"
                # 应该接近白色
                assert r > 100 and g > 100 and b > 100, f"Background seems too dark: {corner}"
                print(f"    ✓ Background is white-based, not black")

    print("\n✓ All tests passed! Transparent backgrounds are properly filled with white.")


if __name__ == "__main__":
    paths = create_test_images()
    test_transparency_detection(paths)
    test_conversion_to_jpg(paths)
