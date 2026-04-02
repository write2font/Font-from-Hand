package com.example.backend.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "autobiographies")
@Getter
@NoArgsConstructor
public class Autobiography {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // JWT 연동 후 팀원이 채워줄 필드 (nullable)
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id")
    private User user;

    @Column(nullable = false)
    private String subjectName;   // 자서전 주인공 이름

    @Column
    private String title;         // 자서전 제목 (AI 생성)

    @Column(nullable = false)
    private String pdfPath;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    public Autobiography(User user, String subjectName, String title, String pdfPath) {
        this.user        = user;
        this.subjectName = subjectName;
        this.title       = title;
        this.pdfPath     = pdfPath;
        this.createdAt   = LocalDateTime.now();
    }
}
