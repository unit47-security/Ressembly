// Resolve a verified Ressembly file-offset reference in the current program.
// GPL-3.0-or-later. No network connection or program mutation.
// @category Ressembly
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.mem.MemoryBlockSourceInfo;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import ghidra.program.database.mem.FileBytes;
import java.math.BigInteger;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.MessageDigest;
import java.io.StringReader;
import com.google.gson.JsonElement;
import com.google.gson.stream.JsonReader;
import com.google.gson.stream.JsonToken;
import java.util.HashSet;
import java.util.Set;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class RessemblyLink extends GhidraScript {
    private void require(boolean condition, String message) throws Exception {
        if (!condition) throw new Exception(message);
    }
    private static final BigInteger LIMIT = BigInteger.ONE.shiftLeft(64);
    private String string(JsonObject object, String key) throws Exception {
        JsonElement value = object.get(key);
        require(value != null && value.isJsonPrimitive() && value.getAsJsonPrimitive().isString(), "Invalid string: " + key);
        return value.getAsString();
    }
    private BigInteger uint(JsonObject object, String key) throws Exception {
        JsonElement value = object.get(key);
        require(value != null && value.isJsonPrimitive() && value.getAsJsonPrimitive().isNumber(), "Invalid integer: " + key);
        String text = value.getAsString();
        require(text.matches("0|[1-9][0-9]*") && text.length() <= 20, "Invalid unsigned integer: " + key);
        BigInteger number = new BigInteger(text);
        require(number.compareTo(LIMIT) < 0, "Integer overflow: " + key);
        return number;
    }
    private JsonObject readReference(String text) throws Exception {
        JsonReader reader = new JsonReader(new StringReader(text));
        reader.setLenient(false);
        JsonObject object = new JsonObject();
        reader.beginObject();
        while (reader.hasNext()) {
            String key = reader.nextName();
            require(!object.has(key), "Duplicate JSON key: " + key);
            // Flat schema: consume primitives directly, preserving exact number spelling.
            JsonToken token = reader.peek();
            require(token == JsonToken.STRING || token == JsonToken.NUMBER, "Invalid reference value: " + key);
            if (token == JsonToken.STRING) object.addProperty(key, reader.nextString());
            else object.add(key, JsonParser.parseString(reader.nextString()));
        }
        reader.endObject();
        require(reader.peek() == JsonToken.END_DOCUMENT, "Trailing JSON content");
        return object;
    }
    private BigInteger u64(ByteBuffer bytes, int offset) {
        long number = bytes.getLong(offset);
        return new BigInteger(Long.toUnsignedString(number));
    }
    private BigInteger elfAddress(byte[] original, long offset) throws Exception {
        require(original.length >= 64, "Short ELF header");
        ByteBuffer b = ByteBuffer.wrap(original).order(ByteOrder.LITTLE_ENDIAN);
        require(b.getInt(0) == 0x464c457f && b.get(4) == 2 && b.get(5) == 1 && b.get(6) == 1,
                "Only ELF64 little-endian version 1 supported");
        require((b.getShort(16) == 2 || b.getShort(16) == 3) && b.getShort(18) == 62 && b.getInt(20) == 1,
                "Only x86-64 executable/shared ELF supported");
        long phoff = u64(b, 32).longValueExact();
        int count = Short.toUnsignedInt(b.getShort(56));
        require(b.getShort(52) == 64 && b.getShort(54) == 56 && count > 0 && count <= 1024 && phoff >= 64
                && phoff <= original.length - 56L * count, "Unsupported or truncated ELF program table");
        BigInteger answer = null, fileSize = BigInteger.valueOf(original.length), position = BigInteger.valueOf(offset);
        for (int index = 0; index < count; index++) {
            int at = (int)(phoff + 56L * index);
            if (b.getInt(at) != 1) continue;
            BigInteger start = u64(b, at + 8), va = u64(b, at + 16), size = u64(b, at + 32), memory = u64(b, at + 40);
            require(size.compareTo(memory) <= 0 && start.add(size).compareTo(fileSize) <= 0
                    && va.add(memory).compareTo(LIMIT) <= 0, "Invalid ELF segment bounds");
            if ((b.getInt(at + 4) & 1) != 0 && position.compareTo(start) >= 0 && position.compareTo(start.add(size)) < 0) {
                require(answer == null, "Ambiguous executable ELF segment");
                answer = va.add(position.subtract(start));
                require(answer.compareTo(LIMIT) < 0, "ELF virtual address overflow");
            }
        }
        require(answer != null, "Offset outside executable ELF segments");
        return answer;
    }
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        require(args.length == 2, "RessemblyLink.java REFERENCE_JSON NEW_RESULT_JSON");
        require(currentProgram != null, "No open program");
        Path input = Path.of(args[0]), output = Path.of(args[1]);
        require(Files.size(input) <= 1048576, "Reference exceeds budget");
        require(currentProgram.getLanguage().getProcessor().toString().equals("x86")
                && !currentProgram.getLanguage().isBigEndian() && currentProgram.getDefaultPointerSize() == 8,
                "Only x86 little-endian 64-bit programs supported");
        JsonObject reference = readReference(Files.readString(input));
        require(string(reference, "schema").equals("ressembly.code-reference.v1"), "Unsupported schema");
        String hash = string(reference, "module_sha256");
        require(hash.matches("[0-9a-f]{64}") && hash.equals(currentProgram.getExecutableSHA256()), "Program build hash mismatch");
        long offset = uint(reference, "file_offset").longValueExact();
        BigInteger pc = uint(reference, "runtime_pc"), start = uint(reference, "mapping_start"), end = uint(reference, "mapping_end");
        BigInteger mappingOffset = uint(reference, "mapping_offset"), elfVA = uint(reference, "elf_virtual_address");
        require(start.compareTo(pc) <= 0 && pc.compareTo(end) < 0
                && pc.subtract(start).add(mappingOffset).equals(BigInteger.valueOf(offset)), "Inconsistent runtime mapping");
        Set<Address> candidates = new HashSet<>();
        Set<FileBytes> sources = new HashSet<>();
        for (MemoryBlock block : currentProgram.getMemory().getBlocks()) {
            if (!block.isExecute()) continue;
            for (MemoryBlockSourceInfo source : block.getSourceInfos()) {
                if (source.getFileBytes().isPresent()) {
                    Address address = source.locateAddressForFileOffset(offset);
                    if (address != null) { candidates.add(address); sources.add(source.getFileBytes().get()); }
                }
            }
        }
        require(candidates.size() == 1, "File offset is unmapped or ambiguous in program");
        require(sources.size() == 1, "Ambiguous original file source");
        FileBytes source = sources.iterator().next();
        require(source.getFileOffset() == 0 && source.getSize() >= 64 && source.getSize() <= 67108864, "Unsupported original file extent");
        byte[] original = new byte[(int)source.getSize()];
        require(source.getOriginalBytes(0, original) == original.length, "Short original file read");
        String originalHash = java.util.HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(original));
        require(originalHash.equals(hash), "Original file hash mismatch");
        require(elfAddress(original, offset).equals(elfVA), "ELF virtual address mismatch");
        Address address = candidates.iterator().next();
        String hex = string(reference, "file_bytes_hex");
        require(hex.matches("[0-9a-f]{2,32}") && hex.length() % 2 == 0, "Invalid code sample");
        byte[] sample = new byte[hex.length()/2];
        require(offset <= original.length - sample.length, "Code sample exceeds original file");
        require(currentProgram.getMemory().getBytes(address, sample) == sample.length, "Short program read");
        for (int index=0; index<sample.length; index++) {
            require((original[(int)offset + index] & 255) == Integer.parseInt(hex.substring(2*index,2*index+2),16), "Reference bytes differ from original file");
            require((sample[index] & 255) == Integer.parseInt(hex.substring(2*index,2*index+2),16), "Program bytes changed from reference");
        }
        Function function = currentProgram.getFunctionManager().getFunctionContaining(address);
        JsonObject result = new JsonObject();
        result.addProperty("schema", "ressembly.ghidra-link.v1");
        result.addProperty("module_sha256", hash);
        result.addProperty("file_offset", offset);
        result.addProperty("ghidra_address", address.toString());
        result.addProperty("program", currentProgram.getName());
        result.addProperty("language", currentProgram.getLanguageID().toString());
        result.addProperty("function", function == null ? null : function.getName());
        result.addProperty("function_entry", function == null ? null : function.getEntryPoint().toString());
        result.addProperty("program_modified", false);
        result.addProperty("evidence", "matching program hash, unique executable file-byte mapping and sampled code bytes");
        Files.writeString(output, new Gson().toJson(result) + "\n", StandardOpenOption.CREATE_NEW);
        if (!isRunningHeadless()) goTo(address);
        println("RESSEMBLY_LINK_OK " + address);
    }
}
