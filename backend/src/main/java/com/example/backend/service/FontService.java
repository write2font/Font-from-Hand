package com.example.backend.service;

import com.example.backend.entity.Font;
import com.example.backend.entity.User;
import com.example.backend.repository.FontRepository;
import com.example.backend.repository.UserRepository;
import com.example.backend.security.JwtProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.*;
import java.nio.file.Paths;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class FontService {

    private final FontRepository fontRepository;
    private final UserRepository userRepository;
    private final JwtProvider jwtProvider;

    @Transactional
    public String uploadFont(List<MultipartFile> files, String token) throws Exception {
        User user = getUserFromToken(token);

        String fontId = UUID.randomUUID().toString();
        String baseDir = System.getProperty("user.dir");
        String uploadPath = Paths.get(baseDir, "uploads", fontId).toString();

        saveFiles(files, uploadPath);

        String pythonScriptPath = Paths.get(baseDir, "..", "font-engine", "main.py").normalize().toString();
        String outputTtfPath = Paths.get(uploadPath, "MyHandwriting.ttf").toString();

        boolean success = runPythonEngine(pythonScriptPath, uploadPath, outputTtfPath);
        if (!success) {
            throw new RuntimeException("파이썬 폰트 생성 중 에러 발생");
        }

        fontRepository.save(new Font(user, "MyHandwriting", fontId, outputTtfPath));
        return fontId;
    }

    @Transactional(readOnly = true)
    public File downloadFont(String token) {
        User user = getUserFromToken(token);

        Font font = fontRepository.findByUserOrderByCreatedAtDesc(user)
            .stream().findFirst()
            .orElseThrow(() -> new RuntimeException("생성된 폰트가 없습니다."));

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
        if (!directory.exists()) directory.mkdirs();

        for (MultipartFile file : files) {
            String originalName = file.getOriginalFilename();
            if (originalName == null) continue;

            String fileNameOnly = originalName.replaceAll("[^0-9]", "");
            String saveName;
            if (!fileNameOnly.isEmpty()) {
                int fileNumber = Integer.parseInt(fileNameOnly);
                saveName = String.format("%02d.jpg", fileNumber);
            } else {
                saveName = originalName;
            }
            file.transferTo(new File(uploadPath + File.separator + saveName));
        }
    }

    private boolean runPythonEngine(String scriptPath, String inputDir, String outputTtfPath) {
        try {
            ProcessBuilder pb = new ProcessBuilder("python3", "-u", scriptPath, inputDir, outputTtfPath);
            pb.redirectErrorStream(true);
            Process process = pb.start();

            BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            while ((line = reader.readLine()) != null) {
                System.out.println("[Python Log] " + line);
            }

            int exitCode = process.waitFor();
            return exitCode == 0;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }
}