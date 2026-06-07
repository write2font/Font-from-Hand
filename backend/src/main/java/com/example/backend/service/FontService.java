package com.example.backend.service;

import com.example.backend.entity.Font;
import com.example.backend.entity.User;
import com.example.backend.repository.FontRepository;
import com.example.backend.repository.UserRepository;
import com.example.backend.security.JwtProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class FontService {

    private final FontRepository fontRepository;
    private final UserRepository userRepository;
    private final JwtProvider jwtProvider;

    @Value("${font.engine.legacy.python-command:python3}")
    private String legacyPythonCommand;

    @Value("${font.engine.handwrite.use-docker:true}")
    private boolean handwriteUseDocker;

    @Value("${font.engine.handwrite.docker-command:docker}")
    private String handwriteDockerCommand;

    @Value("${font.engine.handwrite.docker-image:handwrite2350:latest}")
    private String handwriteDockerImage;

    @Value("${font.engine.handwrite.engine-dir:}")
    private String handwriteEngineDir;

    @Value("${font.engine.handwrite.workers:8}")
    private int handwriteWorkers;

    @Value("${font.engine.ai.use-docker:true}")
    private boolean aiUseDocker;

    @Value("${font.engine.ai.docker-image:write2font-ai:cpu}")
    private String aiDockerImage;

    @Value("${font.engine.ai.engine-dir:}")
    private String aiEngineDir;

    @Value("${font.engine.ai.python-command:python}")
    private String aiPythonCommand;

    @Value("${font.engine.ai.model:DM}")
    private String aiModel;

    @Value("${font.engine.ai.weight-path:}")
    private String aiWeightPath;

    @Transactional
    public String uploadFont(List<MultipartFile> files, String token, String fontName, Font.FontType type, boolean drawMode) throws Exception {
        User user = getUserFromToken(token);

        String fontId = UUID.randomUUID().toString();
        String baseDir = System.getProperty("user.dir");
        String uploadPath = Paths.get(baseDir, "uploads", fontId).toString();
        String inputPath = Paths.get(uploadPath, "input").toString();
        String engineOutputPath = Paths.get(uploadPath, "handwrite-output").toString();
        String outputTtfPath = Paths.get(uploadPath, safeFileName(fontName) + ".ttf").toString();

        saveFiles(files, inputPath);

        boolean success;
        if (type == Font.FontType.AI) {
            success = runAiFontEngine(inputPath, engineOutputPath, outputTtfPath, fontName);
        } else if (type == Font.FontType.MANUAL && !drawMode) {
            success = runHandwrite2350Engine(inputPath, engineOutputPath, outputTtfPath, fontName, user.getName());
        } else {
            String pythonScriptPath = Paths.get(baseDir, "..", "font-engine", "main.py").normalize().toString();
            success = runLegacyPythonEngine(pythonScriptPath, inputPath, outputTtfPath, drawMode);
        }

        if (!success) {
            throw new RuntimeException("폰트 생성 중 오류가 발생했습니다.");
        }

        deleteImageFiles(inputPath);

        fontRepository.save(new Font(user, fontName, fontId, outputTtfPath, type));
        return fontId;
    }

    @Transactional(readOnly = true)
    public List<Font> getMyFonts(String token) {
        User user = getUserFromToken(token);
        return fontRepository.findByUserOrderByCreatedAtDesc(user);
    }

    @Transactional
    public void deleteFont(String token, String fontId) {
        User user = getUserFromToken(token);

        Font font = fontRepository.findByFontId(fontId)
            .filter(f -> f.getUser().getId().equals(user.getId()))
            .orElseThrow(() -> new RuntimeException("폰트를 찾을 수 없습니다."));

        File dir = new File(font.getTtfPath()).getParentFile();
        if (dir != null && dir.exists()) {
            File[] files = dir.listFiles();
            if (files != null) {
                for (File f : files) {
                    f.delete();
                }
            }
            dir.delete();
        }

        fontRepository.delete(font);
    }

    @Transactional(readOnly = true)
    public File downloadFont(String token, String fontId) {
        User user = getUserFromToken(token);

        Font font = fontRepository.findByFontId(fontId)
            .filter(f -> f.getUser().getId().equals(user.getId()))
            .orElseThrow(() -> new RuntimeException("폰트를 찾을 수 없습니다."));

        File ttfFile = new File(font.getTtfPath());
        if (!ttfFile.exists()) {
            throw new RuntimeException("폰트 파일을 찾을 수 없습니다.");
        }
        return ttfFile;
    }

    private User getUserFromToken(String token) {
        if (token == null || !jwtProvider.validateToken(token)) {
            throw new RuntimeException("유효하지 않은 토큰입니다.");
        }
        String email = jwtProvider.getEmailFromToken(token);
        return userRepository.findByEmail(email)
            .orElseThrow(() -> new RuntimeException("유저를 찾을 수 없습니다."));
    }

    private void saveFiles(List<MultipartFile> files, String uploadPath) throws Exception {
        File directory = new File(uploadPath);
        if (!directory.exists()) {
            directory.mkdirs();
        }

        for (MultipartFile file : files) {
            String originalName = file.getOriginalFilename();
            if (originalName == null) {
                continue;
            }

            String fileNameOnly = originalName.replaceAll("[^0-9]", "");
            String saveName;
            if (!fileNameOnly.isEmpty()) {
                int fileNumber = Integer.parseInt(fileNameOnly);
                saveName = String.format("page%02d%s", fileNumber, extensionOrDefault(originalName));
            } else {
                saveName = originalName;
            }
            file.transferTo(new File(uploadPath + File.separator + saveName));
        }
    }

    private String extensionOrDefault(String fileName) {
        int dotIndex = fileName.lastIndexOf('.');
        if (dotIndex >= 0 && dotIndex < fileName.length() - 1) {
            return fileName.substring(dotIndex).toLowerCase();
        }
        return ".jpg";
    }

    private void deleteImageFiles(String uploadPath) {
        File[] imageFiles = new File(uploadPath).listFiles(f -> {
            String name = f.getName().toLowerCase();
            return name.endsWith(".jpg") || name.endsWith(".jpeg") || name.endsWith(".png");
        });
        if (imageFiles != null) {
            for (File image : imageFiles) {
                image.delete();
            }
        }
    }

    private boolean runLegacyPythonEngine(String scriptPath, String inputDir, String outputTtfPath, boolean drawMode) {
        try {
            List<String> cmd = new ArrayList<>(Arrays.asList(legacyPythonCommand, "-u", scriptPath, inputDir, outputTtfPath));
            if (drawMode) {
                cmd.addAll(Arrays.asList("--rows", "1", "--cols", "1"));
            }
            return runCommand(cmd, null, null);
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    private boolean runHandwrite2350Engine(
        String inputDir,
        String engineOutputDir,
        String outputTtfPath,
        String fontName,
        String designer
    ) {
        try {
            cleanDirectory(Paths.get(engineOutputDir));

            List<String> cmd;
            File workingDirectory = null;
            ProcessEnvironmentCustomizer envCustomizer = null;

            if (handwriteUseDocker) {
                cmd = new ArrayList<>(Arrays.asList(
                    handwriteDockerCommand,
                    "run",
                    "--rm",
                    "-v",
                    Paths.get(inputDir).toAbsolutePath() + ":/app/samples/input",
                    "-v",
                    Paths.get(engineOutputDir).toAbsolutePath() + ":/app/outputs",
                    handwriteDockerImage
                ));
            } else {
                Path engineDir = resolveHandwriteEngineDir();
                workingDirectory = engineDir.toFile();
                cmd = new ArrayList<>(Arrays.asList(legacyPythonCommand, "-u", "src/main.py"));
                envCustomizer = environment -> {
                    environment.put("HANDWRITE_INPUT_DIR", Paths.get(inputDir).toAbsolutePath().toString());
                    environment.put("HANDWRITE_OUTPUTS_DIR", Paths.get(engineOutputDir).toAbsolutePath().toString());
                };
            }

            cmd.addAll(Arrays.asList(
                "--fast",
                "--workers",
                String.valueOf(handwriteWorkers),
                "--family-name",
                fontName,
                "--designer",
                designer == null ? "" : designer
            ));

            if (!runCommand(cmd, workingDirectory, envCustomizer)) {
                return false;
            }

            Path generatedTtf = findGeneratedTtf(Paths.get(engineOutputDir, "fonts"));
            Files.copy(generatedTtf, Paths.get(outputTtfPath), StandardCopyOption.REPLACE_EXISTING);
            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    private boolean runAiFontEngine(String inputDir, String engineOutputDir, String outputTtfPath, String fontName) {
        try {
            Path resolvedWeightPath = resolveAiWeightPath();
            Path aiInputPath = resolveAiInputPath(Paths.get(inputDir));
            cleanDirectory(Paths.get(engineOutputDir));

            List<String> cmd;
            File workingDirectory = null;

            if (aiUseDocker) {
                Path inputMountPath = Files.isDirectory(aiInputPath) ? aiInputPath : aiInputPath.getParent();
                String containerInputPath = Files.isDirectory(aiInputPath)
                    ? "/input"
                    : "/input/" + aiInputPath.getFileName();
                Path outputPath = Paths.get(engineOutputDir).toAbsolutePath();
                Path weightParent = resolvedWeightPath.getParent();
                String containerWeightPath = "/weights/" + resolvedWeightPath.getFileName();

                cmd = new ArrayList<>(Arrays.asList(
                    handwriteDockerCommand,
                    "run",
                    "--rm",
                    "-v",
                    inputMountPath + ":/input:ro",
                    "-v",
                    outputPath + ":/output",
                    "-v",
                    weightParent + ":/weights:ro",
                    aiDockerImage,
                    "python",
                    "-X",
                    "utf8",
                    "write2font/run_pipeline.py",
                    "--input",
                    containerInputPath,
                    "--out-ttf",
                    "/output/font.ttf",
                    "--family-name",
                    fontName,
                    "--model",
                    aiModel,
                    "--weight",
                    containerWeightPath,
                    "--python",
                    "python"
                ));
            } else {
                Path engineDir = resolveAiEngineDir();
                workingDirectory = engineDir.toFile();
                cmd = new ArrayList<>(Arrays.asList(
                    aiPythonCommand,
                    "-X",
                    "utf8",
                    "write2font/run_pipeline.py",
                    "--input",
                    aiInputPath.toAbsolutePath().toString(),
                    "--out-ttf",
                    Paths.get(engineOutputDir, "font.ttf").toAbsolutePath().toString(),
                    "--family-name",
                    fontName,
                    "--model",
                    aiModel,
                    "--weight",
                    resolvedWeightPath.toString(),
                    "--python",
                    aiPythonCommand
                ));
            }

            if (!runCommand(cmd, workingDirectory, null)) {
                return false;
            }

            Files.copy(Paths.get(engineOutputDir, "font.ttf"), Paths.get(outputTtfPath), StandardCopyOption.REPLACE_EXISTING);
            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    private boolean runCommand(List<String> cmd, File workingDirectory, ProcessEnvironmentCustomizer envCustomizer) throws Exception {
        ProcessBuilder pb = new ProcessBuilder(cmd);
        if (workingDirectory != null) {
            pb.directory(workingDirectory);
        }
        if (envCustomizer != null) {
            envCustomizer.customize(pb.environment());
        }
        pb.redirectErrorStream(true);
        Process process = pb.start();

        try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println("[Font Engine] " + line);
            }
        }

        int exitCode = process.waitFor();
        return exitCode == 0;
    }

    private Path resolveHandwriteEngineDir() {
        if (handwriteEngineDir != null && !handwriteEngineDir.isBlank()) {
            return Paths.get(handwriteEngineDir).toAbsolutePath().normalize();
        }
        return Paths.get(System.getProperty("user.dir"), "..", "handwrite2350-engine").toAbsolutePath().normalize();
    }

    private Path resolveAiEngineDir() {
        if (aiEngineDir != null && !aiEngineDir.isBlank()) {
            return Paths.get(aiEngineDir).toAbsolutePath().normalize();
        }
        return Paths.get(System.getProperty("user.dir"), "..", "fewshot-font-generation").toAbsolutePath().normalize();
    }

    private Path resolveAiInputPath(Path inputDir) throws IOException {
        Path normalizedInputDir = inputDir.toAbsolutePath().normalize();
        if (!Files.isDirectory(normalizedInputDir)) {
            return normalizedInputDir;
        }

        try (var stream = Files.list(normalizedInputDir)) {
            List<Path> imageFiles = stream
                .filter(Files::isRegularFile)
                .filter(this::isSupportedImageFile)
                .sorted()
                .toList();

            if (imageFiles.size() == 1) {
                return imageFiles.get(0).toAbsolutePath().normalize();
            }

            return normalizedInputDir;
        }
    }

    private Path resolveAiWeightPath() throws FileNotFoundException {
        if (aiWeightPath == null || aiWeightPath.isBlank()) {
            throw new FileNotFoundException("AI font weight path is not configured. Set FONT_ENGINE_AI_WEIGHT_PATH.");
        }
        Path weightPath = Paths.get(aiWeightPath);
        if (!weightPath.isAbsolute()) {
            weightPath = resolveAiEngineDir().resolve(weightPath);
        }
        weightPath = weightPath.toAbsolutePath().normalize();
        if (!Files.exists(weightPath)) {
            throw new FileNotFoundException("AI font weight file not found: " + weightPath);
        }
        return weightPath;
    }

    private void cleanDirectory(Path path) throws IOException {
        if (Files.exists(path)) {
            try (var stream = Files.walk(path)) {
                stream.sorted(Comparator.reverseOrder())
                    .map(Path::toFile)
                    .forEach(File::delete);
            }
        }
        Files.createDirectories(path);
    }

    private boolean isSupportedImageFile(Path path) {
        String name = path.getFileName().toString().toLowerCase();
        return name.endsWith(".png")
            || name.endsWith(".jpg")
            || name.endsWith(".jpeg")
            || name.endsWith(".bmp")
            || name.endsWith(".webp");
    }

    private Path findGeneratedTtf(Path fontsDir) throws IOException {
        if (!Files.isDirectory(fontsDir)) {
            throw new FileNotFoundException("handwrite2350 fonts directory not found: " + fontsDir);
        }
        try (var stream = Files.list(fontsDir)) {
            return stream
                .filter(path -> path.getFileName().toString().toLowerCase().endsWith(".ttf"))
                .findFirst()
                .orElseThrow(() -> new FileNotFoundException("handwrite2350 did not generate a TTF file in " + fontsDir));
        }
    }

    private String safeFileName(String value) {
        String sanitized = value == null ? "" : value.replaceAll("[\\\\/:*?\"<>|]", "_").trim();
        return sanitized.isBlank() ? "MyFont" : sanitized;
    }

    @FunctionalInterface
    private interface ProcessEnvironmentCustomizer {
        void customize(java.util.Map<String, String> environment);
    }
}
