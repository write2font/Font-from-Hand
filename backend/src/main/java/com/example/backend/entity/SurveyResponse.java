package com.example.backend.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Entity
@Table(name = "survey_responses")
@Getter
@NoArgsConstructor
public class SurveyResponse {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "autobiography_id", nullable = false)
    private Autobiography autobiography;

    @Column(nullable = false)
    private String ratings;   // JSON 배열 문자열 ex) "[5,4,3,5,4]"

    @Column(columnDefinition = "TEXT")
    private String freeText;

    @Column(nullable = false)
    private LocalDateTime createdAt;

    public SurveyResponse(Autobiography autobiography, String ratings, String freeText) {
        this.autobiography = autobiography;
        this.ratings       = ratings;
        this.freeText      = freeText;
        this.createdAt     = LocalDateTime.now();
    }
}
