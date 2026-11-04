{
    int n;
    int a;
    int b;
    int t;
    int i;
    read(n);
    a = 0;
    b = 1;
    i = 0;
    while (i < n) {
        t = a + b;
        a = b;
        b = t;
        i = i + 1;
    }
    print(n);
    print(a);
}
