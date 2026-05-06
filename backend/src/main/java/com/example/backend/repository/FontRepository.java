package com.example.backend.repository;

import com.example.backend.entity.Font;
import com.example.backend.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface FontRepository extends JpaRepository<Font, Long> {
    List<Font> findByUserOrderByCreatedAtDesc(User user);
    Optional<Font> findByFontId(String fontId);
}