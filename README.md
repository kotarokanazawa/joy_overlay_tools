# joy_overlay_tools

ROS1 用の `sensor_msgs/Joy` ツール集です。

含まれるノード:

- `joy_overlay_visualizer.py`
  - 既存の `Joy` トピックを透過オーバレイ表示，とパブリッシュも可能

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



# joy_overlay_tools 基本機能

## 1. Virtual Joy GUI

Joyデバイスが無い場合でも、GUIから `sensor_msgs/Joy` を publish できます。

### 機能

- `Layout / Count` から button数 と axis数 をGUI上で変更できます。
- スティック割り当て軸と trigger軸 も同じ画面で変更できます。
- `Save Preset` で現在の構成を保存できます。
- `Load Preset` で保存済み構成を呼び出せます。
- プリセットは既定で `~/.ros/virtual_joy_presets/` に保存されます。
- ボタン、axis、stick をGUI上から操作して `Joy` を publish できます。
- ラベルや要素数の変更内容は設定として保存できます。

### 用途

- 実機コントローラが無い環境でのテスト
- `joy` 入力を必要とするノードの動作確認
- 配列数や割り当ての確認
- プリセットごとの入力構成切り替え


## 2. Joy Overlay Visualizer

既存の `Joy` トピックを、透過オーバレイUIとして画面上に可視化できます。

### 機能

- オーバレイ表示で、コントローラ描画以外は透過されます。
- `Joy` の配列数に応じて button / axis の表示数が自動で追従します。
- button は押下時に色が変わります。
- stick は入力方向と大きさがわかるように表示されます。
- axis bar は値をバー表示できます。
- axis bar は `horizontal` / `vertical` を切り替えできます。
- 右クリックで Editモード を開けます。
- Editモードでは、要素位置のドラッグ移動、index変更、表示文字変更、色変更、サイズ変更ができます。
- Editモードには `描画リセット` があり、描画位置や設定を初期配置に戻せます。
- 設定内容は保存され、次回起動時に引き継がれます。
- Visualizerに `クリックでPublish` モードを追加しました。OFF/ONはEditモードの設定から切り替えできます。
- `クリックでPublish` がONのとき、overlay上の button / axis / stick を直接クリック・ドラッグして `Joy` を publish できます。
- axis bar と stick は左ダブルクリックで初期値 `0` に戻せます。
- overlay上で publish 操作するときは、最初に押した要素だけを継続操作するため、axis と stick の干渉を抑えています。

### 用途

- `Joy` 入力状態の常時確認
- コントローラ入力のデバッグ
- 配列番号と見た目の対応付け
- 実機入力の可視化と簡易入力注入


## 設定保存先

### Virtual Joy GUI
- 通常設定: `~/.ros/virtual_joy_gui.yaml`
- プリセット: `~/.ros/virtual_joy_presets/`

### Joy Overlay Visualizer
- 設定: `~/.ros/joy_overlay_config.yaml`

