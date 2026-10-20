{
    int i; int j;
    i = 1;
    while (i <= 3) {
        j = 1;
        while (j <= 3) {
            if (j > 1) break;
            print(i * 10 + j);
            j = j + 1;
        }
        i = i + 1;
    }
}
