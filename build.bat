./env/script/activate.bat
python setup.py build_ext --inplace
pyinstaller --noconfirm --onedir --console --icon "./icon.ico" --add-data "./tool.exe;." --add-data "./img;img/" --paths "./src" --hidden-import "logic.skill" --hidden-import "logic.leader" "./chihiro.py"
rm ./src/*.c ./src/*.pyd ./src/logic/*.c ./src/logic/*.pyd