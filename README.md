# import mixamo - root motion
这是一个blender插件，用来批量导入Mixamo.com下载的fbx文件，并可以创建一个根骨骼记录位移信息。
`blender` `add-ons` `batch import` `fbx` `mixamo.com ` `root motion` 

## 已知问题
Root Motion 烘焙动画到根骨骼后，新的动画会和原来的动画有一点细小的误差，这种误差会导致循环出现卡顿现象。

> 原因：骨骼动画使用（Local）局部空间坐标系，而且Hips骨骼初始y轴并不是与世界坐标z轴重合，有一定旋转角度，而动画中也包含有旋转的关键帧动画。所有当Hips骨骼的旋转角度越大，误差也就越大，使得动画循环出现问题。

<font color="gray" size=2>正在尝试修复中...</font>

## 功能：
- 批量导入Fbx文件
- 批量去除前缀名称 "mixamorig:"
- 批量重命名动画名称，以文件名命名
- 批量应用所有变换并修复动画强度
- 批量移除多余的骨架和物体 "Armature.00*"
- 创建根骨骼记录位移信息
- Root Motion 提供了两种方式烘焙根位移动画到根骨骼

## 使用方法：
1. 安装Blender 4.10或更高版本。
2. 下载并安装该插件。
3. 打开Blender，选择“文件”>“导入”>“Mixamo Fbx(floder/*.fbx)”。
4. 在打开的对话框中，选择动画文件的文件夹，右侧面板进行设置，点击导入“Import Mixamo *.Fbx”。

![001](./img/001.png)
![002](./img/002.png)
![003](./img/003.png)
![004](./img/004.gif)
![005](./img/005.gif)
![006](./img/006.gif)


<font color=gray>~~搞掂！~~</font>
<font color=gray>~~坐翻低、饮啖茶、吃个包 🍵🫖🍞~~</font>
