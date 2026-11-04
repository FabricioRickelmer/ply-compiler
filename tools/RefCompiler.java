import java.nio.file.Files;
import java.nio.file.Paths;
import lexer.Lexer;
import parser.Parser;

public class RefCompiler {
    public static void main(String[] args) {
        if (args.length == 0) {
            System.err.println("Usage: RefCompiler <file.uc>");
            System.exit(1);
        }
        try {
            String code = new String(Files.readAllBytes(Paths.get(args[0])));
            Lexer lexer = new Lexer();
            lexer.setInputText(code);
            Parser parser = new Parser(lexer);
            parser.setGenerateCode(true);
            parser.program();
            System.out.println("SUCESSO");
        } catch (Throwable t) {
            System.err.println(t.getMessage());
            System.exit(1);
        }
    }
}
