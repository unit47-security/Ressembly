// Exchange a static review selection with the Ressembly evidence viewer.
// GPL-3.0-or-later.
// @category Ressembly
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import java.io.File;
import java.io.InputStream;
import java.io.StringReader;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.List;
import java.util.Set;

public class RessemblyReview extends GhidraScript {
    private static final String SCHEMA = "ressembly.ghidra-review.v1";
    private static final Set<String> FIELDS =
        Set.of("schema", "executable_sha256", "program", "language", "function");
    private static final int MAX_BYTES = 8192;

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalArgumentException(message);
    }

    private static String bounded(String value) {
        require(value != null && !value.isBlank() && value.length() <= 512 &&
            value.codePoints().noneMatch(Character::isISOControl), "Invalid review text");
        return value;
    }

    private Function uniqueFunction(String qualifiedName) throws Exception {
        bounded(qualifiedName);
        Function match = null;
        int visited = 0;
        for (Function function : currentProgram.getFunctionManager().getFunctions(true)) {
            monitor.checkCancelled();
            require(++visited <= 100000, "Function lookup exceeds budget");
            if (qualifiedName.equals(function.getName(true))) {
                require(match == null, "Ambiguous qualified function name");
                match = function;
            }
        }
        require(match != null, "Named function is absent from this program");
        return match;
    }

    private JsonObject readReview(Path file) throws Exception {
        byte[] bytes;
        try (InputStream input = Files.newInputStream(file)) {
            bytes = input.readNBytes(MAX_BYTES + 1);
        }
        require(bytes.length <= MAX_BYTES, "Review file exceeds size budget");
        String raw = StandardCharsets.UTF_8.newDecoder().decode(ByteBuffer.wrap(bytes)).toString();
        JsonObject data = new JsonObject();
        try (JsonReader reader = new JsonReader(new StringReader(raw))) {
            reader.setLenient(false);
            reader.beginObject();
            while (reader.hasNext()) {
                String name = reader.nextName();
                require(FIELDS.contains(name) && !data.has(name) && reader.peek() == JsonToken.STRING,
                    "Unexpected or duplicate review field");
                data.addProperty(name, bounded(reader.nextString()));
            }
            reader.endObject();
            require(reader.peek() == JsonToken.END_DOCUMENT, "Trailing review content");
        }
        require(data.keySet().equals(FIELDS) && SCHEMA.equals(data.get("schema").getAsString()),
            "Invalid review schema");
        return data;
    }

    @Override
    public void run() throws Exception {
        require(currentProgram != null, "Open a program first");
        String hash = currentProgram.getExecutableSHA256();
        require(hash != null && hash.matches("[0-9a-f]{64}"), "Program has no executable SHA-256");
        String language = currentProgram.getLanguageID().toString();
        String[] args = getScriptArgs();
        String action;
        Path path;
        if (args.length == 0) {
            action = askChoice("Ressembly review", "Action", List.of("export", "open"), "export");
            File selection = askFile("Ressembly review JSON", action.equals("export") ? "Save" : "Open");
            if (selection == null) return;
            path = selection.toPath();
        } else {
            require((args.length == 3 && args[0].equals("export")) ||
                (args.length == 2 && args[0].equals("open")),
                "Use export NEW_JSON QUALIFIED_NAME or open REVIEW_JSON");
            action = args[0];
            path = Path.of(args[1]);
        }
        if (action.equals("export")) {
            Function selected = args.length == 3 ? uniqueFunction(args[2]) :
                currentAddress == null ? null : currentProgram.getFunctionManager()
                    .getFunctionContaining(currentAddress);
            require(selected != null, "Place the cursor inside a function");
            String name = selected.getName(true);
            if (args.length == 0) uniqueFunction(name);
            JsonObject data = new JsonObject();
            data.addProperty("schema", SCHEMA);
            data.addProperty("executable_sha256", hash);
            data.addProperty("program", bounded(currentProgram.getName()));
            data.addProperty("language", bounded(language));
            data.addProperty("function", bounded(name));
            String encoded = new Gson().toJson(data) + "\n";
            require(encoded.getBytes(StandardCharsets.UTF_8).length <= MAX_BYTES,
                "Review record exceeds size budget");
            Files.writeString(path, encoded, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
            println("RESSEMBLY_REVIEW_EXPORTED");
        } else {
            JsonObject data = readReview(path);
            require(hash.equals(data.get("executable_sha256").getAsString()) &&
                language.equals(data.get("language").getAsString()), "Program identity mismatch");
            Function selected = uniqueFunction(data.get("function").getAsString());
            if (!isRunningHeadless()) {
                require(goTo(selected.getEntryPoint()), "Could not navigate to selected function");
            }
            println("RESSEMBLY_REVIEW_RESOLVED");
        }
    }
}
