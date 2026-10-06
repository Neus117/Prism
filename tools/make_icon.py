"""一次性脚本：生成扁平渐变风格的 3D 棱锥图标。"""
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw

# 配置路径
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "prism.ico"
OUT.parent.mkdir(parents=True, exist_ok=True)

SIZE = 256
SS = 4  # 超采样倍数，用于抗锯齿
W, H = SIZE * SS, SIZE * SS

STROKE = 5                      # 最终尺寸下的棱边宽度（px）
GRAY = (128, 128, 128, 255)     # 棱边纯灰色
WHITE_EXPAND = 4.0              # 白色扩展强度，值越大白色越多


def get_barycentric(P, A, B, C):
    """计算点 P 相对于三角形 ABC 的重心坐标 (u, v, w)。"""
    v0 = C - A
    v1 = B - A
    v2 = P - A
    dot00 = np.sum(v0 * v0)
    dot01 = np.sum(v0 * v1)
    dot02 = np.sum(v0 * v2, axis=-1)
    dot11 = np.sum(v1 * v1)
    dot12 = np.sum(v1 * v2, axis=-1)
    inv_denom = 1.0 / (dot00 * dot11 - dot01 * dot01)
    u = (dot11 * dot02 - dot01 * dot12) * inv_denom
    v = (dot00 * dot12 - dot01 * dot02) * inv_denom
    w = 1.0 - u - v
    return u, v, w


def apply_white_expand(u, v, w, p=WHITE_EXPAND):
    """让顶部顶点权重 w 非线性放大，从而扩大白色区域。"""
    w_new = 1.0 - (1.0 - w) ** p
    rest = u + v
    scale = np.where(rest > 1e-8, (1.0 - w_new) / rest, 0.0)
    return u * scale, v * scale, w_new


def generate_prism_icon():
    # 1. 几何顶点设定（模拟 3D 透视，底边有向前的折角）
    apex = np.array([W / 2, H * 0.16], dtype=np.float32)
    left = np.array([W * 0.15, H * 0.80], dtype=np.float32)
    right = np.array([W * 0.85, H * 0.80], dtype=np.float32)
    front = np.array([W / 2, H * 0.90], dtype=np.float32)

    # 2. 颜色锚点
    c_apex = np.array([255, 255, 255], dtype=np.float32)
    c_left = np.array([0, 230, 120], dtype=np.float32)
    c_right = np.array([255, 60, 90], dtype=np.float32)
    c_front = np.array([130, 40, 255], dtype=np.float32)

    # 3. 像素网格
    Y, X = np.mgrid[0:H, 0:W]
    P = np.stack([X, Y], axis=-1).astype(np.float32)

    # 4. 左面渐变
    u_l, v_l, w_l = get_barycentric(P, apex, left, front)
    mask_left = (u_l >= 0) & (v_l >= 0) & (w_l >= 0)
    u_l, v_l, w_l = apply_white_expand(u_l, v_l, w_l)
    color_left = (w_l[..., None] * c_apex +
                  v_l[..., None] * c_left +
                  u_l[..., None] * c_front)

    # 5. 右面渐变
    u_r, v_r, w_r = get_barycentric(P, apex, right, front)
    mask_right = (u_r >= 0) & (v_r >= 0) & (w_r >= 0)
    u_r, v_r, w_r = apply_white_expand(u_r, v_r, w_r)
    color_right = (w_r[..., None] * c_apex +
                   v_r[..., None] * c_right +
                   u_r[..., None] * c_front)

    # 6. 合成两个渐变面
    img_arr = np.zeros((H, W, 3), dtype=np.float32)
    img_arr[mask_left] = color_left[mask_left]
    img_arr[mask_right] = color_right[mask_right]
    img_arr = np.clip(img_arr, 0, 255).astype(np.uint8)
    face = Image.fromarray(img_arr, "RGB").convert("RGBA")

    # 7. 用三角形遮罩裁出主体（背景保持透明）
    body_mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(body_mask).polygon(
        [tuple(apex), tuple(left), tuple(front), tuple(right)], fill=255
    )
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img.paste(face, (0, 0), body_mask)

    # 8. 纯灰色粗描边：外轮廓 + 中间棱线
    draw = ImageDraw.Draw(img)
    outline = [tuple(apex), tuple(left), tuple(front), tuple(right), tuple(apex)]
    draw.line(outline, fill=GRAY, width=STROKE * SS, joint="curve")
    draw.line([tuple(apex), tuple(front)], fill=GRAY, width=STROKE * SS)

    # 9. 缩放输出
    img = img.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    return img


if __name__ == "__main__":
    print("🎨 正在生成扁平渐变风格 Prism 图标...")
    icon_img = generate_prism_icon()
    icon_img.save(
        OUT,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    print(f"✅ 已生成 {OUT}")