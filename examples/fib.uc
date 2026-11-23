{
    int n;
    int k;
    int f1;
    int f2;
    int f3;
    read(n);
    f1 = 0;
    f2 = 1;
    k = 1;
    while (k <= n) {
        f3 = f1 + f2;
        f1 = f2;
        f2 = f3;
        k = k + 1;
    }
    print(n);
    print(f1);
}
