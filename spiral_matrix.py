"""
螺旋矩阵 II — 给定正整数 n，生成 n×n 矩阵，元素 1~n² 按顺时针螺旋排列。

思路：维护上下左右四条边界，按 右→下→左→上 的顺序逐层填充。
每填完一条边，收缩对应边界。当数字超过 n² 时停止。
时间复杂度 O(n²)，空间复杂度 O(1)（不计结果矩阵）。
"""

def generate_spiral_matrix(n: int) -> list[list[int]]:
    matrix = [[0] * n for _ in range(n)]

    top, bottom = 0, n - 1
    left, right = 0, n - 1
    num = 1

    while num <= n * n:
        # 向右 → 填充 top 行
        for col in range(left, right + 1):
            matrix[top][col] = num
            num += 1
        top += 1  # 上边界下移

        # 向下 ↓ 填充 right 列
        for row in range(top, bottom + 1):
            matrix[row][right] = num
            num += 1
        right -= 1  # 右边界左移

        # 向左 ← 填充 bottom 行
        if top <= bottom:  # 避免奇数 n 时重复填充
            for col in range(right, left - 1, -1):
                matrix[bottom][col] = num
                num += 1
            bottom -= 1  # 下边界上移

        # 向上 ↑ 填充 left 列
        if left <= right:
            for row in range(bottom, top - 1, -1):
                matrix[row][left] = num
                num += 1
            left += 1  # 左边界右移

    return matrix


# ---------- 测试 ----------
if __name__ == "__main__":
    for n in [1, 2, 3, 4]:
        result = generate_spiral_matrix(n)
        print(f"n = {n}")
        for row in result:
            print("  ", row)
        print()
