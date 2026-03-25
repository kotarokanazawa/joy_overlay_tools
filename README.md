# joy_overlay_tools

ROS1 用の `sensor_msgs/Joy` ツール集です。

含まれるノード:

- `joy_overlay_visualizer.py`
  - 既存の `Joy` トピックを透過オーバレイ表示
- `virtual_joy_gui.py`
  - Joy デバイスが無いときに GUI から `Joy` を publish

## 依存

```bash
sudo apt install ros-noetic-rospy ros-noetic-sensor-msgs python3-pyqt5 python3-yaml
```

## ビルド

```bash
cd ~/catkin_ws/src
cp -r joy_overlay_tools ~/catkin_ws/src/
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

## 1. Joy 可視化

```bash
roslaunch joy_overlay_tools joy_overlay_visualizer.launch joy_topic:=/joy
```

- 右クリックで Edit モード用の編集ウィンドウ
- `Esc` で Edit モード終了
- `Ctrl+C` で終了
- 左ドラッグでウィンドウ移動

## 2. GUI で Joy を publish

```bash
roslaunch joy_overlay_tools virtual_joy_gui.launch joy_topic:=/joy_virtual
```

操作:

- 左右スティック: マウスドラッグ
- ボタン: クリックで ON/OFF
- trigger / extra axes: スライダ
- Reset: 全入力を 0 に戻す
- Label Edit: ボタン名・軸名を変更して保存

## 3. GUI publish と overlay 表示を同時に起動

```bash
roslaunch joy_overlay_tools virtual_joy_with_overlay.launch joy_topic:=/joy_virtual
```

## 主なパラメータ

### virtual_joy_gui.py

- `~joy_topic` : publish 先トピック
- `~num_buttons` : ボタン数
- `~num_axes` : 軸数
- `~publish_rate` : publish 周波数
- `~config_path` : 設定 YAML

### joy_overlay_visualizer.py

- `~joy_topic` : subscribe する Joy トピック
- `~config_path` : overlay 設定 YAML

## 設定ファイル

- 仮想 Joy GUI: `~/.ros/virtual_joy_gui.yaml`
- Overlay: `~/.ros/joy_overlay_config.yaml`


- OverlayのAxis表示は、Editモードから horizontal / vertical を切り替え可能です。
- Editモード説明パネルは縮小時でも見切れにくいように調整しています。


## Virtual Joy 追加機能

- `Layout / Count` から button数 と axis数 をGUI上で変更できます。
- スティック割り当て軸と trigger軸 も同じ画面で変更できます。
- `Save Preset` で現在の構成を保存できます。
- `Load Preset` で保存済み構成を呼び出せます。
- プリセットは既定で `~/.ros/virtual_joy_presets/` に保存されます。