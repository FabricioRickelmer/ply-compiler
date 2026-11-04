import os

files = {
    'atribuicao.uc': '{\n    float x;\n    int y;\n    y = 42;\n    x = y;\n    print(x);\n}\n',
    'blocos.uc': '{\n    int a;\n    a = 1;\n    {\n        int a;\n        a = 2;\n        print(a);\n    }\n    print(a);\n}\n',
    'charlit.uc': "{\n    char c;\n    c = 'a';\n    print(c + 1);\n}\n",
    'logica.uc': '{\n    int x;\n    x = 0;\n    if (true && !false || false) {\n        x = 1;\n    }\n    print(x);\n}\n',
    'relacionais.uc': '{\n    int a;\n    int b;\n    a = 10;\n    b = 20;\n    if (a < b && b >= 20 && a != b && a == 10) {\n        print(1);\n    } else {\n        print(0);\n    }\n}\n',
    'leitura.uc': '{\n    int x;\n    read(x);\n    print(x * 2);\n}\n',
    'decl_multipla.uc': '{\n    int a, b, c;\n    a = 1;\n    b = 2;\n    c = 3;\n    print(a + b + c);\n}\n'
}

for name, content in files.items():
    with open(os.path.join('examples', name), 'w', encoding='utf-8') as f:
        f.write(content)
print('New valid examples created successfully.')
