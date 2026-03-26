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


## 修正
- joy_overlay_visualizer.py の Edit モード説明文の構文エラーを修正しました。
- virtual_joy_gui.py の QPainter drawLine による DeprecationWarning を修正しました。

- VisualizerのEditモードに「描画リセット」を追加し、ボタン・axis・stickの描画位置や設定を初期レイアウトへ戻せます。

- Visualizerに「クリックでPublish」モードを追加しました。OFF/ONはEditモードの設定から切り替えできます。ONのとき、overlay上の button / axis / stick を直接クリック・ドラッグして Joy を publish できます。

- OverlayのPublish操作で、axisとstickの干渉を抑えました。押し始めた要素だけを継続操作します。
- axis bar と stick は左ダブルクリックで初期値 0 に戻せます。

- VisualizerのクリックPublishで、axis / stick を離したときに値を保持するか 0 に戻すかを設定で選べます。
- VisualizerはJoy入力が無くても、設定済みの button / axis / stick を描画します。

- `クリックでPublish` がONのときは、通常の左クリックを入力操作に優先し、ウィンドウ移動は `Shift + 左ドラッグ` のときだけ有効にしました。

- Editモードで各要素に対して Assign 機能を追加しました。Assign開始中は対象要素が赤くなり、次に実機ジョイスティックで入力された button / axis をその要素へ割り当てられます。
