# 反弹相关的运动学模型

## 基本反弹模型

当一个小球与边界发生弹性碰撞时，其法向速度反向，切向速度不变，即：

$$
\boldsymbol{v}_0 = \boldsymbol{v}_{-1} - (1 + e)(\boldsymbol{v}_{-1} \cdot \boldsymbol{n}) \boldsymbol{n}
$$

其中：

- $\boldsymbol{v}_{-1}$​：碰撞前的速度向量
- $\boldsymbol{v}_{0}$ ：碰撞后的速度向量
- $\boldsymbol{n}$：碰撞点处边界的**单位外法向量**
- $e$​：**恢复系数**，表示法向速度的保持比例

## 抛体运动方程

仅考虑重力，小球抛体运动方程为：

$$
\boldsymbol{p}(t) =\boldsymbol{p}_0 + \boldsymbol{v}_0 t + \frac{1}{2} \boldsymbol{a} t^2
$$

结合碰撞方程，可得：

$$
\begin{align}
\boldsymbol{p}(t)
&= \boldsymbol{p}_0 +( \boldsymbol{v}_{-1} + k\boldsymbol{n}) t + \frac{1}{2} \boldsymbol{a} t^2 \\
&= \boldsymbol{r}(t) + kt\boldsymbol{n}
\end{align}
$$

其中：

- $\boldsymbol{r}(t)=\boldsymbol{p}_0+\boldsymbol{v}_{-1}t+\frac{1}{2}\boldsymbol{a}t^2$ 为中间变量
- $\boldsymbol{p}(t)$：某一时刻的位置
- $\boldsymbol{p}_{0}$​ ：运动的初始位置
- $\boldsymbol{a}$：仅考虑常数的情形

## 计算恢复系数

问题描述：给定终端时间 $t = t_f$ 与和边界类型相关的约束 $f(\boldsymbol{p}_f)=0$ ，求解$k$，进而求解得到期望恢复系数：
$$
e = \frac{-k}{\boldsymbol{v}_{-1} \cdot \boldsymbol{n}} - 1
$$

### 圆形边界

圆形边界的约束为：
$$
\left\| \boldsymbol{p}_f \right\|^2 = R^2
$$

于是有：

$$
\left\| \boldsymbol{p}_f \right\|^2 = \left\| \boldsymbol{r}_f \right\|^2 + 2kt_f (\boldsymbol{r}_f\cdot\boldsymbol{n}) + k^2t_f^2 = R^2
$$

整理为一元二次方程：

$$
A k^2 + B k + C = 0
$$

其中：

- $A = t_f^2$
- $B = 2t_f (\boldsymbol{r}_f \cdot \boldsymbol{n})$
- $C = \|\boldsymbol{r}_f\|^2 - R^2$

求解一元二次方程得到 $k$ ，进而反推出期望恢复系数

> 前面给出的约束条件并非充要条件，理论上还有另外一个约束条件
> $$
> \forall t \in [0, t_f], \left\|\boldsymbol{p}(t)\right\| \le R
> $$
>
> 不满足该约束条件的解对应了球曾飞出边界并在终端时间返回的情形，可以在解析求解后额外验证筛选。

### 椭圆边界

使用二次型隐式表示椭圆边界：
$$
\boldsymbol{p}^\mathrm{T}\boldsymbol{Q}\boldsymbol{p} - 1 = 0
$$
其中$\boldsymbol{Q}=\mathrm{diag}(1/a^2,1/b^2)$。其上任意一点的外法向为：
$$
\boldsymbol{n}=\frac{\boldsymbol{Q}\boldsymbol{p}}{\left\|\boldsymbol{Q}\boldsymbol{p}\right\|}
$$
最终同样获得了一个一元二次方程：
$$
\boldsymbol{p}_f^\mathrm{T}\boldsymbol{Q}\boldsymbol{p}_f - 1= A k^2 + B k + C = 0
$$
其中：

- $A = t_f^2\boldsymbol{n}^\mathrm{T}\boldsymbol{Q}\boldsymbol{n}$
- $B = 2t_f (\boldsymbol{r}_f^\mathrm{T}\boldsymbol{Q}\boldsymbol{n})$
- $C = \boldsymbol{r}_f^\mathrm{T}\boldsymbol{Q}\boldsymbol{r}_f - 1$

> 显然，上面的圆形边界只不过是一个特例，椭圆边界情形给出了更加一般的结论
>
> 但是若考虑球自身的尺寸，膨胀后的外轮廓就不再是椭圆...
>
> 同时，椭圆边界难以求解出比较理想的碰撞序列，可能圆的某些良好性质被破坏了...
