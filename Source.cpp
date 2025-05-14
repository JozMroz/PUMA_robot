#define _CRT_SECURE_NO_WARNING
#include <vector>
#include <string>
#define GLAD_GL_IMPLEMENTATION
#include <glad/glad.h> 
#define GLFW_INCLUDE_NONE
#include <GLFW/glfw3.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>
#include <iostream>
#include <vector>
#include <cmath>

// Vertex Shader Source
const char* vertexShaderSource = R"(
    #version 330 core
    layout (location = 0) in vec3 aPos;

    uniform mat4 model;
    uniform mat4 view;
    uniform mat4 projection;

    void main()
    {
        gl_Position = projection * view * model * vec4(aPos, 1.0);
    }
)";

// Fragment Shader Source
const char* fragmentShaderSource = R"(
    #version 330 core
    out vec4 FragColor;

    uniform vec4 color;

    void main()
    {
        FragColor = color;
    }
)";

// Function to compile shaders
GLuint compileShader(GLenum type, const char* source) {
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);

    int success;
    char infoLog[512];
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        glGetShaderInfoLog(shader, 512, nullptr, infoLog);
        std::cerr << "ERROR::SHADER::COMPILATION_FAILED\n" << infoLog << std::endl;
    }
    return shader;
}

// Function to create shader program
GLuint createShaderProgram() {
    GLuint vertexShader = compileShader(GL_VERTEX_SHADER, vertexShaderSource);
    GLuint fragmentShader = compileShader(GL_FRAGMENT_SHADER, fragmentShaderSource);

    GLuint shaderProgram = glCreateProgram();
    glAttachShader(shaderProgram, vertexShader);
    glAttachShader(shaderProgram, fragmentShader);
    glLinkProgram(shaderProgram);

    int success;
    char infoLog[512];
    glGetProgramiv(shaderProgram, GL_LINK_STATUS, &success);
    if (!success) {
        glGetProgramInfoLog(shaderProgram, 512, nullptr, infoLog);
        std::cerr << "ERROR::SHADER::PROGRAM::LINKING_FAILED\n" << infoLog << std::endl;
    }

    glDeleteShader(vertexShader);
    glDeleteShader(fragmentShader);

    return shaderProgram;
}

// Robot position and angles
float posX = 0.0f, posY = 0.0f;
float baseAngle = 0.0f;
float armAngle = 0.0f;
float armAngle1 = 0.0f;
float hookAngle = 0.0f;
bool hookOpen = false;

// Key callback function
void key_callback(GLFWwindow* window, int key, int scancode, int action, int mods) {
    if (action == GLFW_PRESS || action == GLFW_REPEAT) {
        switch (key) {
        case GLFW_KEY_W:
            posY += 0.1f;
            break;
        case GLFW_KEY_S:
            posY -= 0.1f;
            break;
        case GLFW_KEY_A:
            posX -= 0.1f;
            break;
        case GLFW_KEY_D:
            posX += 0.1f;
            break;
        case GLFW_KEY_Q:
            baseAngle += 5.0f;
            break;
        case GLFW_KEY_E:
            baseAngle -= 5.0f;
            break;
        case GLFW_KEY_R:
            armAngle += 5.0f;
            break;
        case GLFW_KEY_F:
            armAngle -= 5.0f;
            break;
        case GLFW_KEY_T:
            armAngle1 += 5.0f;
            break;
        case GLFW_KEY_G:
            armAngle1 -= 5.0f;
            break;
        case GLFW_KEY_H:
            hookOpen = !hookOpen;
            hookAngle = hookOpen ? 20.0f : 0.0f;
            break;
        case GLFW_KEY_ESCAPE:
            glfwSetWindowShouldClose(window, GLFW_TRUE);
            break;
        }
    }
}

// Function to generate cylinder vertices
std::vector<float> generateCylinderVertices(float radius, float height, int segments) {
    std::vector<float> vertices;
    for (int i = 0; i <= segments; ++i) {
        float theta = 2.0f * glm::pi<float>() * float(i) / float(segments); // angle
        float x = radius * cosf(theta); // x coordinate
        float z = radius * sinf(theta); // z coordinate

        // bottom circle
        vertices.push_back(x);
        vertices.push_back(0.0f);
        vertices.push_back(z);

        // top circle
        vertices.push_back(x);
        vertices.push_back(height);
        vertices.push_back(z);
    }

    return vertices;
}
void generateSphere(std::vector<float>& vertices, std::vector<unsigned int>& indices, float radius, int sectorCount, int stackCount) {
    float x, y, z, xy;
    float sectorStep = 2 * glm::pi<float>() / sectorCount;
    float stackStep = glm::pi<float>() / stackCount;
    float sectorAngle, stackAngle;

    for (int i = 0; i <= stackCount; ++i) {
        stackAngle = glm::pi<float>() / 2 - i * stackStep;
        xy = radius * cosf(stackAngle);
        z = radius * sinf(stackAngle);

        for (int j = 0; j <= sectorCount; ++j) {
            sectorAngle = j * sectorStep;
            x = xy * cosf(sectorAngle);
            y = xy * sinf(sectorAngle);
            vertices.push_back(x);
            vertices.push_back(y);
            vertices.push_back(z);
        }
    }

    for (int i = 0; i < stackCount; ++i) {
        int k1 = i * (sectorCount + 1);
        int k2 = k1 + sectorCount + 1;

        for (int j = 0; j < sectorCount; ++j, ++k1, ++k2) {
            if (i != 0) {
                indices.push_back(k1);
                indices.push_back(k2);
                indices.push_back(k1 + 1);
            }

            if (i != (stackCount - 1)) {
                indices.push_back(k1 + 1);
                indices.push_back(k2);
                indices.push_back(k2 + 1);
            }
        }
    }
}

void drawSphere(GLuint shaderProgram, GLuint VAO, int indexCount, glm::mat4 model, glm::vec4 color) {
    glUniform4fv(glGetUniformLocation(shaderProgram, "color"), 1, glm::value_ptr(color));
    glUniformMatrix4fv(glGetUniformLocation(shaderProgram, "model"), 1, GL_FALSE, glm::value_ptr(model));
    glBindVertexArray(VAO);
    glDrawElements(GL_TRIANGLES, indexCount, GL_UNSIGNED_INT, 0);
}

// Function to draw a cube
void drawCube(GLuint shaderProgram, GLuint VAO, glm::mat4 model, glm::vec4 color) {
    glUniform4fv(glGetUniformLocation(shaderProgram, "color"), 1, glm::value_ptr(color));
    glUniformMatrix4fv(glGetUniformLocation(shaderProgram, "model"), 1, GL_FALSE, glm::value_ptr(model));
    glBindVertexArray(VAO);
    glDrawArrays(GL_TRIANGLES, 0, 36);
}

// Function to draw a cylinder
void drawCylinder(GLuint shaderProgram, GLuint VAO, const glm::mat4& model, glm::vec4 color, int segments) {
    glUniform4fv(glGetUniformLocation(shaderProgram, "color"), 1, glm::value_ptr(color));
    glUniformMatrix4fv(glGetUniformLocation(shaderProgram, "model"), 1, GL_FALSE, glm::value_ptr(model));
    glBindVertexArray(VAO);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, (segments + 1) * 2);
}

// Main function
int main() {
    // Initialize GLFW
    if (!glfwInit()) {
        std::cerr << "Failed to initialize GLFW" << std::endl;
        return -1;
    }

    // Create a windowed mode window and its OpenGL context
    GLFWwindow* window = glfwCreateWindow(1400, 1200, "Simple Robot PUMA", nullptr, nullptr);
    if (!window) {
        std::cerr << "Failed to create GLFW window" << std::endl;
        glfwTerminate();
        return -1;
    }

    // Make the window's context current
    glfwMakeContextCurrent(window);

    // Load OpenGL functions using GLAD
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) {
        std::cerr << "Failed to initialize GLAD" << std::endl;
        return -1;
    }

    // Compile and link shaders
    GLuint shaderProgram = createShaderProgram();

    // Set up vertex data and buffers and configure vertex attributes for the cube
    float cubeVertices[] = {
        // positions
        -0.15f, -0.15f, -0.15f,
         0.15f, -0.15f, -0.15f,
         0.15f,  0.15f, -0.15f,
         0.15f,  0.15f, -0.15f,
        -0.15f,  0.15f, -0.15f,
        -0.15f, -0.15f, -0.15f,

        -0.15f, -0.15f,  0.15f,
         0.15f, -0.15f,  0.15f,
         0.15f,  0.15f,  0.15f,
         0.15f,  0.15f,  0.15f,
        -0.15f,  0.15f,  0.15f,
        -0.15f, -0.15f,  0.15f,

        -0.15f,  0.15f,  0.15f,
        -0.15f,  0.15f, -0.15f,
        -0.15f, -0.15f, -0.15f,
        -0.15f, -0.15f, -0.15f,
        -0.15f, -0.15f,  0.15f,
        -0.15f,  0.15f,  0.15f,

         0.15f,  0.15f,  0.15f,
         0.15f,  0.15f, -0.15f,
         0.15f, -0.15f, -0.15f,
         0.15f, -0.15f, -0.15f,
         0.15f, -0.15f,  0.15f,
         0.15f,  0.15f,  0.15f,

        -0.15f, -0.15f, -0.15f,
         0.15f, -0.15f, -0.15f,
         0.15f, -0.15f,  0.15f,
         0.15f, -0.15f,  0.15f,
        -0.15f, -0.15f,  0.15f,
        -0.15f, -0.15f, -0.15f,

        -0.15f,  0.15f, -0.15f,
         0.15f,  0.15f, -0.15f,
         0.15f,  0.15f,  0.15f,
         0.15f,  0.15f,  0.15f,
        -0.15f,  0.15f,  0.15f,
        -0.15f,  0.15f, -0.15f
    };

    GLuint cubeVBO, cubeVAO;
    glGenVertexArrays(1, &cubeVAO);
    glGenBuffers(1, &cubeVBO);

    glBindVertexArray(cubeVAO);

    glBindBuffer(GL_ARRAY_BUFFER, cubeVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(cubeVertices), cubeVertices, GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);


    // Set up vertex data and buffers for the cylinder
    std::vector<float> cylinderVertices = generateCylinderVertices(0.1f, 1.0f, 32);

    GLuint cylinderVBO, cylinderVAO;
    glGenVertexArrays(1, &cylinderVAO);
    glGenBuffers(1, &cylinderVBO);

    glBindVertexArray(cylinderVAO);

    glBindBuffer(GL_ARRAY_BUFFER, cylinderVBO);
    glBufferData(GL_ARRAY_BUFFER, cylinderVertices.size() * sizeof(float), cylinderVertices.data(), GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    float radius = 1.0f;
    int sectorCount = 72;
    int stackCount = 36;
    std::vector<float> sphereVertices;
    std::vector<unsigned int> sphereIndices;
    generateSphere(sphereVertices, sphereIndices, radius, sectorCount, stackCount);

    GLuint sphereVAO, sphereVBO, sphereEBO;
    glGenVertexArrays(1, &sphereVAO);
    glGenBuffers(1, &sphereVBO);
    glGenBuffers(1, &sphereEBO);

    glBindVertexArray(sphereVAO);

    glBindBuffer(GL_ARRAY_BUFFER, sphereVBO);
    glBufferData(GL_ARRAY_BUFFER, sphereVertices.size() * sizeof(float), &sphereVertices[0], GL_STATIC_DRAW);

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, sphereEBO);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, sphereIndices.size() * sizeof(unsigned int), &sphereIndices[0], GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    // Set the key callback
    glfwSetKeyCallback(window, key_callback);

    // Enable depth test
    glEnable(GL_DEPTH_TEST);

    // Main loop
    while (!glfwWindowShouldClose(window)) {
        // Render here
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        // Use the shader program
        glUseProgram(shaderProgram);

        // Create view and projection matrices
        glm::mat4 view = glm::lookAt(glm::vec3(4.0f, 3.0f, 10.0f), glm::vec3(0.0f, 0.0f, 0.0f), glm::vec3(0.0f, 1.0f, 0.0f));
        glm::mat4 projection = glm::perspective(glm::radians(45.0f), 1400.0f / 1200.0f, 0.1f, 100.0f);

        // Set the view and projection matrices in the shader
        glUniformMatrix4fv(glGetUniformLocation(shaderProgram, "view"), 1, GL_FALSE, glm::value_ptr(view));
        glUniformMatrix4fv(glGetUniformLocation(shaderProgram, "projection"), 1, GL_FALSE, glm::value_ptr(projection));

        // Draw the base
        glm::mat4 model = glm::mat4(1.0f);
        model = glm::translate(model, glm::vec3(posX, posY, 0.0f));
        
        model = glm::scale(model, glm::vec3(80.0f, 0.01f, 80.0f));
        drawCube(shaderProgram, cubeVAO, model, glm::vec4(0.6f, 0.3f, 0.0f, 0.7f)); // brown
        model = glm::scale(model, glm::vec3(0.0125f, 100.0f, 0.0125f));
        drawSphere(shaderProgram, sphereVAO, sphereIndices.size(), model, glm::vec4(1.0f, 0.5f, 0.0f, 1.0f));
        model = glm::translate(model, glm::vec3(0.0f, 0.15f, 0.0f));
        model = glm::scale(model, glm::vec3(4.0f, 1.0f, 4.0f));
        
        drawCube(shaderProgram, cubeVAO, model, glm::vec4(1.0f, 0.0f, 0.0f, 1.0f)); // red

        // Draw the base-to-arm cylinder
        model = glm::scale(model, glm::vec3(0.25f, 1.0f, 0.25f));
        model = glm::translate(model, glm::vec3(0.0f, 0.15f, 0.0f));
        model = glm::rotate(model, glm::radians(baseAngle), glm::vec3(0.0f, 1.0f, 0.0f));
        drawCylinder(shaderProgram, cylinderVAO, model, glm::vec4(0.0f, 1.0f, 0.0f, 1.0f), 32); // green

        // Draw the arm
        model = glm::translate(model, glm::vec3(0.0f, 1.0f, 0.0f));
        model = glm::rotate(model, glm::radians(armAngle), glm::vec3(1.0f, 0.0f, 0.0f));
        drawCube(shaderProgram, cubeVAO, model, glm::vec4(0.0f, 0.0f, 1.0f, 1.0f)); // blue

        // Draw the arm-to-arm1 cylinder
        model = glm::translate(model, glm::vec3(0.0f, 0.15f, 0.0f));
        drawCylinder(shaderProgram, cylinderVAO, model, glm::vec4(1.0f, 1.0f, 0.0f, 1.0f), 32); // yellow

       
        // Draw the arm1
        model = glm::translate(model, glm::vec3(0.0f, 1.0f, 0.0f));
        model = glm::rotate(model, glm::radians(armAngle1), glm::vec3(1.0f, 0.0f, 0.0f));
        drawCube(shaderProgram, cubeVAO, model, glm::vec4(0.0f, 0.0f, 1.0f, 1.0f)); // blue

        // Draw the arm1-to-hook cylinder
        model = glm::translate(model, glm::vec3(0.0f, 0.15f, 0.0f));
        drawCylinder(shaderProgram, cylinderVAO, model, glm::vec4(1.0f, 1.0f, 0.0f, 1.0f), 32); // yellow

        // Draw the hook
        model = glm::translate(model, glm::vec3(0.0f, 1.0f, 0.0f));
        model = glm::rotate(model, glm::radians(hookAngle), glm::vec3(0.0f, 0.0f, 1.0f));
        model = glm::scale(model, glm::vec3(2.5f, 0.2f, 1.0f));
       
        drawCube(shaderProgram, cubeVAO, model, glm::vec4(1.0f, 0.0f, 1.0f, 1.0f)); // magenta
        model = glm::scale(model, glm::vec3(0.4f, 5.0f, 1.0f));
        model = glm::translate(model, glm::vec3(0.4f, 0.27f, 0.0f));
        model = glm::scale(model, glm::vec3(0.2f, 2.0f, 1.0f));
        drawCube(shaderProgram, cubeVAO, model, glm::vec4(1.0f, 0.5f, 1.0f, 1.0f)); // magenta
        model = glm::scale(model, glm::vec3(5.0f, 0.5f, 1.0f));
        model = glm::translate(model, glm::vec3(-0.4f, -0.27f, 0.0f));
        model = glm::translate(model, glm::vec3(-0.4f, 0.27f, 0.0f));
        model = glm::scale(model, glm::vec3(0.2f, 2.0f, 1.0f));
        drawCube(shaderProgram, cubeVAO, model, glm::vec4(1.0f, 0.5f, 1.0f, 1.0f));
         // magenta

        // Swap front and back buffers
        glfwSwapBuffers(window);

        // Poll for and process events
        glfwPollEvents();
    }

    // Deallocate resources
    glDeleteVertexArrays(1, &cubeVAO);
    glDeleteBuffers(1, &cubeVBO);
    glDeleteVertexArrays(1, &cylinderVAO);
    glDeleteBuffers(1, &cylinderVBO);
    glDeleteProgram(shaderProgram);

    glfwTerminate();
    return 0;
}